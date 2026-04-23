import sys
import os
import re

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.gems import GemsParser

def test_inv_parsing():
    print("--- Testing GEMS Invoice Parsing ---")
    parser = GemsParser()
    
    # Mock Token Stream for "Split Invoice"
    # Case 1: Date, Head, PatID, Tail
    # "01/01/24", "AOP1234", "55555", "67890" (InvTail)
    # Expected: Inv=AOP123467890, PatID=55555
    
    # We can't easily mock `tokens` inside parse without modifying the class or creating a dummy file.
    # But `GemsParser` logic is inside `parse`.
    # I'll subclass or mock the pdf extraction? 
    # Better to copy-paste the loop for testing or use a dummy PDF?
    # I'll creating a dummy PDF is hard. 
    # I will modify GemsParser to accept tokens for testing or just create a new function in this script with the SAME logic.
    
    # Let's extract the logic to a function here to test it quickly.
    
    tokens = [
        "01/01/2024", 
        "AOP1234",  # Head (7 chars)
        "55555",    # PatID (5 chars)
        "67890",    # Tail (5 chars)
        "John", "Doe",
        "123-456",
        "100.00"
    ]
    
    print(f"Tokens: {tokens}")
    rows = run_parser_logic(tokens)
    for r in rows:
        print(f"Result Inv: {r['inv']}, PatID: {r['pat_id']}")
        
    print("-" * 20)
    
    # Case 2: Date, Head, Tail, PatID (If tail comes first)
    tokens2 = [
        "01/01/2024", 
        "AOP1234",  # Head
        "67890",    # Tail
        "55555",    # PatID
        "Jane", "Doe",
        "123-456",
        "200.00"
    ]
    print(f"Tokens2: {tokens2}")
    rows = run_parser_logic(tokens2)
    for r in rows:
        print(f"Result Inv: {r['inv']}, PatID: {r['pat_id']}")

def run_parser_logic(tokens):
    # Copy of GemsParser loop logic (simplified)
    records = []
    current = None
    name_buffer = []
    name_line_count = 0
    step_counter = 0
    pat_id_capture_step = 0
    inv_tail_capture_step = 0
    
    DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
    AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
    MEMBER_NO_RE = re.compile(r'^\d+-\d+$')

    for token in tokens:
        token = token.strip()
        if not token: continue
        
        if DATE_RE.match(token):
            if current:
                records.append(current)
            current = {
                "date": token,
                "inv_prefix": "",
                "inv_suffix": "",
                "pat_id": "",
                "name": "",
                "amounts": []
            }
            name_buffer = [] 
            step_counter = 0
            pat_id_capture_step = 0
            inv_tail_capture_step = 0
            continue
        
        step_counter += 1
        if not current: continue

        curr_inv_len = len(current["inv_prefix"]) + len(current["inv_suffix"])
        
        # Inv Prefix
        if not current["inv_prefix"]:
            chk_token = token.upper()
            if chk_token.startswith("AOP") or chk_token.startswith("AIP"):
                current["inv_prefix"] = chk_token[:3]
                if len(token) > 3:
                     current["inv_suffix"] += token[3:]
                continue

        # Inv Suffix
        if current["inv_prefix"] and curr_inv_len < 14:
             if not AMOUNT_RE.match(token):
                 clean_tok = token.replace("-", "").replace(".", "") 
                 if clean_tok.isdigit():
                     needed = 14 - curr_inv_len
                     if len(clean_tok) <= needed:
                         current["inv_suffix"] += clean_tok
                         inv_tail_capture_step = step_counter
                         continue
        
        # Pat ID Logic (Simplified from GemsParser)
        # Check digit
        if token.isdigit():
            if token == "0": continue
            
            if not current["pat_id"]:
                 full_inv = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "")
                 if len(full_inv) >= 3:
                     if len(token) in [5, 6]:
                          current["pat_id"] = token
                          pat_id_capture_step = step_counter
            else:
                 # Logic to append to Inv if it looks like Suffix
                 # "If it is AOP there are 4 digit after them, then it should take 5 digits from below"
                 full_inv = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "")
                 if len(full_inv) < 14:
                      clean_tok = token.replace("-", "").replace(".", "")
                      if clean_tok.isdigit() and not AMOUNT_RE.match(token):
                           if len(full_inv) + len(clean_tok) <= 14:
                               current["inv_suffix"] += clean_tok
                               inv_tail_capture_step = step_counter
                               continue
    
    if current: records.append(current)
    
    # Post Processing Swap Check (Copied from GemsParser)
    final_rows = []
    for current in records:
        inv_str = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "").upper()
        pat_str = current["pat_id"]
        
        if pat_id_capture_step > inv_tail_capture_step and pat_str and len(inv_str) >= 12:
             # Swap logic
             tail_len = len(pat_str)
             potential_pat = inv_str[-tail_len:]
             
             if potential_pat.isdigit() and pat_str.startswith("0") and not potential_pat.startswith("0"):
                 current["inv_suffix"] = current["inv_suffix"][:-tail_len] + pat_str
                 current["pat_id"] = potential_pat
                 print("SWAP TRIGGERED")
        
        final_rows.append({
            "inv": (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "").upper(),
            "pat_id": current["pat_id"]
        })
    return final_rows

if __name__ == "__main__":
    test_inv_parsing()
