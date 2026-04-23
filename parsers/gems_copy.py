import pdfplumber
import re
from parsers.base import BaseParser

# Regex Definitions - Adjusted for Token Matching
DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP)', re.IGNORECASE)
INV_SUFFIX_RE = re.compile(r'^\d+$')
MEMBER_NO_RE = re.compile(r'^\d+-\d+$')
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$') # Requires decimal part .XX or .XXX

class GemsParser(BaseParser):
    def __init__(self):
        # Raw headers (14 Columns)
        self.raw_headers = [
            "Date Of Treatement", "Invoice No", "Pat. File No.", "Member Name", "Member No.", 
            "Claimed Amount", "Medical", "Financial", "Uncovered", "Total", "Deductible", 
            "Net Payment", "Client Deductible", "Bank charge to Client"
        ]
        # Formatted headers - 9 Columns
        self.formatted_headers = [
            "Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", 
            "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"
        ]

    def parse(self, file_path):
        records = []
        
        with pdfplumber.open(file_path) as pdf:
            tokens = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text = text.replace("\n", " ^NL^ ")
                    tokens.extend(text.split())
            
        current = None
        name_buffer = []
        name_line_count = 0 
        pat_id_capture_step = 0
        inv_tail_capture_step = 0
        # CRITICAL: Initialize here
        newline_seen_since_inv = False
        step_counter = 0

        for token in tokens:
            token = token.strip()
            if not token: continue
            
            # handle line marker
            if token == "^NL^":
                if current:
                     newline_seen_since_inv = True
                     if current["pat_id"]:
                        name_line_count += 1
                continue

            # ---- START NEW RECORD (Date) ----
            if DATE_RE.match(token):
                if current:
                    current["name"] = " ".join(name_buffer)
                    records.append(current)

                current = {
                    "date": token,
                    "inv_prefix": "",
                    "inv_suffix": "",
                    "pat_id": "",
                    "name": "",
                    "member_no": "",
                    "amounts": []
                }
                name_buffer = [] 
                pat_id_capture_step = 0
                inv_tail_capture_step = 0
                newline_seen_since_inv = False
                step_counter = 0
                continue
            
            step_counter += 1

            if not current:
                continue

            # ---- INVOICE LOGIC (Smart Accumulation) ----
            curr_inv_len = len(current["inv_prefix"]) + len(current["inv_suffix"])
            
            # Case 1: Found Prefix (AOP/AIP)
            if not current["inv_prefix"]:
                chk_token = token.upper()
                if chk_token.startswith("AOP") or chk_token.startswith("AIP"):
                    current["inv_prefix"] = chk_token[:3]
                    if len(token) > 3:
                        current["inv_suffix"] += token[3:]
                    newline_seen_since_inv = False
                    continue

            # Case 2: Have Prefix, Need Suffix Digits
            # Strict Length: 12 (AOP=3 + 4 + 5)
            if current["inv_prefix"] and curr_inv_len < 12:
                can_take_suffix = False
                clean_tok = token.replace("-", "").replace(".", "") 
                
                # Ignore isolated zero -> Fixes "Extra 0" bug
                if clean_tok == "0":
                    continue
                
                # Check Overrun
                if clean_tok.isdigit() and not AMOUNT_RE.match(token):
                     needed = 12 - curr_inv_len
                     
                     # Heuristic: Don't fill a large gap (>=3) with a tiny token (<3)
                     # Unless it completes the invoice exactly? No, 1 digit completing 5 digit gap is impossible.
                     # But 1 digit filling 1 digit gap is fine.
                     if len(clean_tok) < 3 and needed >= 3:
                         can_take_suffix = False
                     elif len(clean_tok) <= needed:
                          can_take_suffix = True
                
                if can_take_suffix:
                     # Heuristic: If we have PatID, or if this is "Below" (NewLine Seen) and we are at split point
                     should_force_suffix = False
                     # "If AOP + 4 digits (Len 7), take 5 digits from below"
                     if curr_inv_len == 7 and len(clean_tok) == 5 and newline_seen_since_inv:
                          should_force_suffix = True
                          
                     is_pat_candidate = (len(token) in [5, 6])
                     
                     if should_force_suffix or not is_pat_candidate or current["pat_id"]:
                          current["inv_suffix"] += clean_tok
                          inv_tail_capture_step = step_counter
                          continue
            
            # ---- MEMBER NO ----
            if MEMBER_NO_RE.match(token):
                current["member_no"] = token
                continue

            # ---- AMOUNTS ----
            if AMOUNT_RE.match(token):
                current["amounts"].append(token)
                continue

            # ---- NAME / PAT ID ----
            if token.isdigit():
                if token == "0": continue

                if not current["pat_id"]:
                    # CRITICAL: Only look for Pat ID if Invoice has accumulated SOME content
                    full_inv = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "")
                    # Relaxed check: Just need prefix
                    if len(full_inv) >= 3:
                        if len(token) in [5, 6]:
                             current["pat_id"] = token
                             pat_id_capture_step = step_counter
                             name_line_count = 0 
                else:
                     # WE HAVE PAT ID, but is Inv short?
                     full_inv = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "")
                     if len(full_inv) < 12 and len(token) > 0:
                         clean_tok = token.replace("-", "").replace(".", "")
                         if clean_tok.isdigit() and not AMOUNT_RE.match(token) and clean_tok != "0":
                              needed = 12 - len(full_inv)
                              # Same heuristic: Block small tokens for large gaps
                              if len(clean_tok) < 3 and needed >= 3:
                                  pass
                              elif len(full_inv) + len(clean_tok) <= 12:
                                  current["inv_suffix"] += clean_tok
                                  inv_tail_capture_step = step_counter
                                  continue
                     if name_line_count < 3:
                         if token not in ["0"]:
                             name_buffer.append(token)
            else:
                if name_line_count >= 3:
                    continue
                if token in ["The", "Net", "Payable", "Page", "Claims", "Authorized", "Signatory", "System", "Braze"]:
                     if name_buffer: continue 
                name_buffer.append(token)

        # Save last
        if current:
            # POST-PROCESSING SWAP LOGIC (Copied)
            inv_str = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "").upper()
            pat_str = current["pat_id"]
            
            if pat_id_capture_step > inv_tail_capture_step and pat_str and len(inv_str) >= 12:
                 # Check if Inv ends with something that looks like a PatID (5/6 digits)
                 # And PatID token looks like a Suffix (digits)
                 
                 # Assume Suffix Length matches PatID Length? Or check last 5/6?
                 # Case 2: Inv ends in 20683 (5). PatID is 03723 (5).
                 tail_len = len(pat_str) # Assume symmetrical swap 
                 potential_pat = inv_str[-tail_len:]
                 
                 if potential_pat.isdigit() and pat_str.startswith("0") and not potential_pat.startswith("0"): # ignore zero tokens
                     current["inv_suffix"] = current["inv_suffix"][:-tail_len] + pat_str
                     current["pat_id"] = potential_pat

            current["name"] = " ".join(name_buffer)
            # Final Validation Last Record
            inv = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "").upper()
            if (inv.startswith("AOP") or inv.startswith("AIP")) and len(inv) >= 3:
                records.append(current)

        rows = []
        for r in records:
            inv = (r["inv_prefix"] + r["inv_suffix"]).replace(" ", "").upper()
            if not (inv.startswith("AOP") or inv.startswith("AIP")):
                continue
            
            amts = r["amounts"]
            def get_amt(i):
                val = amts[i] if i < len(amts) else "0.000"
                return val.replace(',', '')
            
            rows.append((
                r["date"],      # 0
                inv,            # 1
                r["pat_id"],    # 2
                r["name"],      # 3
                r["member_no"], # 4
                get_amt(0),     # 5
                get_amt(1),     # 6
                get_amt(2),     # 7
                get_amt(3),     # 8
                get_amt(4),     # 9
                get_amt(5),     # 10
                get_amt(6),     # 11
                get_amt(7),     # 12
                get_amt(8)      # 13
            ))
            
        return rows

    def transform(self, raw_data):
        formatted_rows = []
        sl_no_counter = 1  # Manual counter for sequential numbering

        for row in raw_data:
            # row: Tuple of 14 elements
            # 0:Date, 1:Inv, 2:PatID, 3:Name, 4:MemNo, 5..13:Amounts
            
            date = row[0]
            inv = row[1].upper() # Normalize to Upper Case
            pat_id = row[2]
            name = row[3]
            mem_no = row[4]
            net_payment = row[5] # Index 11 is Net Payment
            amt_to_adjust = row[11] 
            remark = row[4] 

            # --- Validations ---
            
            # Filter: If no valid Invoice No, skip this row entirely
            if not inv.startswith("AOP") and not inv.startswith("AIP"):
                continue

            # Pat ID: Exact 5 or 6 digits
            if len(pat_id) not in [5, 6]:
                pat_id = ""
                
            # Name Cleaning
            name = name.strip()
            while "  " in name: name = name.replace("  ", " ")

            # Construct row 
            # Output Schema: 
            # 1. Sl. No
            # 2. Inv No
            # 3. Date
            # 4. Patient ID
            # 5. Patient Name
            # 6. Invoice Balance (Net Payment)
            # 7. Amt To Adjust (Empty)
            # 8. CustomerCode (Member No)
            # 9. Remark (Empty)

            new_row = [
                sl_no_counter,  # Sl. No
                inv,            # Inv No
                date,           # Date
                pat_id,         # Patient ID
                name,           # Patient Name
                net_payment,    # Invoice Balance
                amt_to_adjust,             # Amt To Adjust
                "",         # CustomerCode
                remark              # Remark
            ]
            
            formatted_rows.append(new_row)
            sl_no_counter += 1
            
        return self.formatted_headers, formatted_rows
