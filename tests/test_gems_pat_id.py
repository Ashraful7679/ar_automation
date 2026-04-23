import re

# Mocking the Regex and Logic from gems.py
DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP)', re.IGNORECASE)
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')

def parse_mock(tokens):
    records = []
    current = None
    name_buffer = []
    name_line_count = 0
    step_counter = 0
    pat_id_capture_step = 0
    inv_tail_capture_step = 0
    
    # Mock loop
    for token in tokens:
        token = token.strip()
        if not token: continue
        
        step_counter += 1

        # New Record
        if DATE_RE.match(token):
            if current:
                 # ---- POST PROCESSING SWAP ----
                inv_str = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "").upper()
                pat_str = current["pat_id"]
                if pat_id_capture_step > inv_tail_capture_step and pat_str and len(inv_str) >= 12:
                     tail_len = len(pat_str)
                     potential_pat = inv_str[-tail_len:]
                     if potential_pat.isdigit():
                         print(f"DEBUG: Swapping! InvTail {potential_pat} <-> PatID {pat_str}")
                         current["inv_suffix"] = current["inv_suffix"][:-tail_len] + pat_str
                         current["pat_id"] = potential_pat

                current["name"] = " ".join(name_buffer)
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
            pat_id_capture_step = 0
            inv_tail_capture_step = 0
            continue

        if not current: continue

        # Smart Accumulation
        curr_inv_len = len(current["inv_prefix"]) + len(current["inv_suffix"])
        
        # Case 1: Prefix
        if not current["inv_prefix"]:
            chk = token.upper()
            if chk.startswith("AOP") or chk.startswith("AIP"):
                current["inv_prefix"] = chk[:3]
                if len(token) > 3: current["inv_suffix"] += token[3:]
                continue
        
        # Case 2: Suffix
        if current["inv_prefix"] and curr_inv_len < 14:
            # GUARD AMOUNT
            if not AMOUNT_RE.match(token):
                clean_tok = token.replace("-", "").replace(".", "")
            else:
                clean_tok = "" 

            if clean_tok.isdigit():
                needed = 14 - curr_inv_len
                if len(clean_tok) > needed:
                    pass
                else:
                    # print(f"DEBUG: Consuming {token} into Inv.")
                    current["inv_suffix"] += clean_tok
                    inv_tail_capture_step = step_counter
                    continue

        # Pat ID Logic
        if token.isdigit():
             if token == "0": continue
             if not current["pat_id"]:
                 full_inv = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "")
                 # RELAXED CHECK: >= 3
                 if len(full_inv) >= 3:
                     if len(token) in [5, 6]:
                         # print(f"DEBUG: Captured Pat ID {token}")
                         current["pat_id"] = token
                         pat_id_capture_step = step_counter
                 else:
                     pass
             else:
                 # POST-PAT ACCUMULATION
                 full_inv = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "")
                 if len(full_inv) < 14 and len(token) > 0:
                      clean_tok = token.replace("-", "").replace(".", "")
                      if clean_tok.isdigit() and not AMOUNT_RE.match(token):
                           if len(full_inv) + len(clean_tok) <= 14:
                               # print(f"DEBUG: Late Accumulate {token} into Inv")
                               current["inv_suffix"] += clean_tok
                               inv_tail_capture_step = step_counter
                               continue

                 name_buffer.append(token)
        else:
            name_buffer.append(token)

    if current:
        # ---- POST PROCESSING SWAP ----
        inv_str = (current["inv_prefix"] + current["inv_suffix"]).replace(" ", "").upper()
        pat_str = current["pat_id"]
        if pat_id_capture_step > inv_tail_capture_step and pat_str and len(inv_str) >= 12:
             tail_len = len(pat_str)
             potential_pat = inv_str[-tail_len:]
             if potential_pat.isdigit() and pat_str.startswith("0") and not potential_pat.startswith("0"):
                 print(f"DEBUG: Swapping! InvTail {potential_pat} <-> PatID {pat_str}")
                 current["inv_suffix"] = current["inv_suffix"][:-tail_len] + pat_str
                 current["pat_id"] = potential_pat

        current["name"] = " ".join(name_buffer)
        records.append(current)
    
    return records

# Scenarios
scenarios = [
    {
        "name": "Case 1: Suffix inside Name (Split)",
        # 01/06/2025 AOP06250 204151 DALAL AHMED 00373 YUSUF ALMANEA
        # Expect: Inv=AOP0625000373, PatID=204151
        "tokens": ["01/06/2025", "AOP06250", "204151", "DALAL", "AHMED", "00373", "YUSUF", "ALMANEA"]
    },
    {
        "name": "Case 2: Pat ID merged in Inv (Overrun)",
        # 12/06/2025 AOP062520683 03723 NAWAF ...
        # Expect: Inv=AOP062503723, PatID=20683
        "tokens": ["12/06/2025", "AOP062520683", "03723", "NAWAF", "JASIM"]
    }
]

for s in scenarios:
    print(f"\n--- Scenario: {s['name']} ---")
    recs = parse_mock(s["tokens"])
    for r in recs:
        full_inv = r["inv_prefix"] + r['inv_suffix']
        print(f"Result: Date={r['date']}, Inv={full_inv} (Len {len(full_inv)}), PatID={r['pat_id']}")
