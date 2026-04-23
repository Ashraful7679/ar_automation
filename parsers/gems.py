import pdfplumber
import re
from parsers.base import BaseParser

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
INV_STRICT_RE = re.compile(r'^(?:AOP|AIP|BOP|COP|HSP|RSP)\d{9}$', re.IGNORECASE)
PAT_FILE_RE = re.compile(r'^\d{5,6}$')
MEMBER_NO_RE = re.compile(r'^\d+-\d+$')
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
NOISE_RE = re.compile(r'\d{2}/\d{2}/\d{4}\d+')
INVOICE_START_RE = re.compile(r'^(\d{5})(/[A-Z]{1,3})')
CONTINUATION_RE = re.compile(r'^(\d{3,5})(?:\s+[A-Za-z].*)?$')

class GemsParser(BaseParser):
    def __init__(self):
        self.raw_headers = [
            "Date Of Treatement", "Invoice No", "Pat. File No.", "Member Name", "Member No.", 
            "Claimed Amount", "Medical", "Financial", "Uncovered", "Total", "Deductible", 
            "Net Payment", "Client Deductible", "Bank charge to Client"
        ]
        self.formatted_headers = [
            "Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", 
            "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"
        ]

    def parse(self, file_path):
        records = []
        
        all_lines = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_lines.extend(text.split("\n"))

        current = None
        last_prefix = None
        last_date = None
        pending_save = None  # Track if we have a record waiting to be saved
        
        for line in all_lines:
            line = line.strip()
            if not line: continue

            # Check for invoice continuation/invoice start lines
            # These should be processed if invoice is incomplete, REGARDLESS of whether we have amounts
            if current:
                # Count only alphanumeric characters (prefix + digits), ignore /XX suffix
                inv_clean = re.sub(r'[^A-Za-z0-9]', '', current['inv_str'])
                needs_more = len(inv_clean) < 12
                
                inv_start_match = INVOICE_START_RE.match(line)
                if inv_start_match and needs_more:
                    # Current invoice is incomplete - append to current, don't create new record
                    digits = inv_start_match.group(1)
                    suffix = inv_start_match.group(2)
                    inv_clean = current['inv_str'].replace('/', '').replace(' ', '')
                    needed = 12 - len(inv_clean)
                    if needed > 0:
                        current['inv_str'] += digits[:needed]
                        if suffix:
                            current['inv_str'] += suffix
                    # Don't add rest to name_parts - it's just part of the continuation pattern
                    # The name after the invoice number is not the patient name
                    continue
                
                cont_match = CONTINUATION_RE.match(line)
                if cont_match and needs_more:
                    digits = cont_match.group(1)
                    needed = 12 - len(inv_clean)
                    if needed > 0:
                        current['inv_str'] += digits[:needed]
                    # Don't add rest to names - it's continuation
                    continue
                
                # Check for P1124XXX pattern (second invoice part) even if invoice is complete
                p_pattern_match = re.match(r'^[Pp]\d{7}$', line)
                if p_pattern_match and not needs_more and current.get('amounts'):
                    # This is continuation for second invoice - add to inv_str
                    current['inv_str'] += ' ' + line
                    continue
                
                # Check for 2-digit suffix (last part of second invoice)
                if re.match(r'^\d{2}$', line.strip()) and not needs_more and current.get('amounts'):
                    if re.search(r'[Pp]\d{7}', current.get('inv_str', '')):
                        # We have P pattern already, this is the suffix
                        current['inv_str'] += ' ' + line.strip()
                        continue
                
                # If invoice is complete (>=12 chars) and we see invoice start pattern, check if it's a NEW record
                if inv_start_match and not needs_more:
                    # This is a separate invoice - save current and create new
                    if current.get('amounts') and current.get('inv_str'):
                        records.append(current)
                    
                    digits = inv_start_match.group(1)
                    suffix = inv_start_match.group(2)
                    
                    current = {
                        'date': last_date,
                        'inv_str': digits + suffix,
                        'pat_id': '',
                        'name_parts': [],
                        'member_no': '',
                        'amounts': [],
                        'remarks': [],
                        'is_complete': False
                    }
                    
                    if last_prefix:
                        current['inv_str'] = last_prefix + current['inv_str']
                    
                    continue

            date_match = DATE_RE.match(line.split()[0]) if line.split() else None
            
            if date_match:
                parts = line.split()
                has_data_token = False
                if len(parts) > 1:
                    for p in parts[1:]:
                        if INV_PREFIX_RE.match(p) or p.isdigit():
                            has_data_token = True
                            break
                
                if not has_data_token:
                    continue
                
                # Don't save immediately on date line - we might still be collecting remarks
                # Instead, just set up the new record context
                # The actual save happens when we hit the next date line (confirming we have a complete record)
                
                last_date = date_match.group()
                
                # IMPORTANT: When we hit a new date line, finalize the PREVIOUS record first
                # This ensures remarks are attached to the correct record
                if current and current.get('amounts') and current.get('inv_str'):
                    records.append(current)
                
                # Now start new record
                
                for p in line.split()[1:]:
                    if INV_PREFIX_RE.match(p):
                        last_prefix = p[:7]
                        break
                
                current = {
                    'date': last_date,
                    'inv_str': '',
                    'pat_id': '',
                    'name_parts': [],
                    'member_no': '',
                    'amounts': [],
                    'remarks': [],
                    'is_complete': False
                }
                
                parts = line.split()
                if len(parts) > 1:
                    skipped_digits = ''
                    
                    for p in parts[1:]:
                        if INV_PREFIX_RE.match(p):
                            current['inv_str'] += p
                        elif '/' in p and not p.startswith('/'):
                            if INV_PREFIX_RE.match(p.split('/')[0]) or p.split('/')[0].isdigit():
                                current['inv_str'] += p
                        elif p.isdigit():
                            if current['inv_str']:
                                inv_clean = current['inv_str'].replace('/', '').replace(' ', '')
                                if len(inv_clean) < 7:
                                    current['inv_str'] += p
                                else:
                                    skipped_digits += p
                            else:
                                skipped_digits += p
                        elif MEMBER_NO_RE.match(p):
                            current['member_no'] = p
                            current['_name_collected'] = True  # Stop collecting name after member_no
                        elif AMOUNT_RE.match(p):
                            current['amounts'].append(p)
                            current['_name_collected'] = True  # Mark name collected from date line
                            # Don't break - continue to check if there are more amounts on same line
                        elif not (INV_PREFIX_RE.match(p) or p.isdigit() or '/' in p):
                            if not current.get('_name_collected'):
                                current['name_parts'].append(p)
                    
                    current['_skipped_digits'] = skipped_digits
                    
                    if skipped_digits and PAT_FILE_RE.match(skipped_digits):
                        current['pat_id'] = skipped_digits
                
                continue
            
            if not current: continue

            # For remarks, collect ALL consecutive lines starting with / or "Remarks :"
            # Also include continuation lines (like "payable." that follow "/As per...")
            if line.startswith('Remarks :') or line.startswith('/') or (line == 'payable.' and current.get('remarks')):
                # Add this remark
                remark_text = line.replace('Remarks :', '').strip()
                current['remarks'].append(remark_text)
                continue

            # Process tokens - but only if invoice is incomplete (needs more digits)
            # Even if we have amounts, we may need to add more to the invoice
            inv_clean = re.sub(r'[^A-Za-z0-9]', '', current['inv_str']) if current.get('inv_str') else ''
            needs_more_invoice = len(inv_clean) < 12
            
            # If we already have a complete invoice (12 chars), we might still be adding to it
            # Check for P1124XXX patterns or 2-digit suffixes that could be second invoice parts
            if not needs_more_invoice and current.get('amounts'):
                # Check if this line has invoice continuation patterns
                has_p_pattern = re.search(r'[Pp]\d{7}', line)
                has_2digit_suffix = re.match(r'^\d{2}$', line.strip())
                
                if has_p_pattern or has_2digit_suffix:
                    # This is likely a continuation for second invoice - process it
                    # Don't skip, fall through to processing
                    pass
                else:
                    # Invoice is complete and no continuation pattern - skip
                    continue
                # Fall through to processing below
            
            if not current['amounts'] or needs_more_invoice or current.get('amounts'):
                parts = line.split()
                if not parts: continue

                for p in parts:
                    if NOISE_RE.match(p):
                        continue
                    
                    if PAT_FILE_RE.match(p) and not current['pat_id']:
                        current['pat_id'] = p
                        continue
                    
                    is_inv_component = False
                    if INV_PREFIX_RE.search(p):
                        is_inv_component = True
                    elif '/' in p:
                        is_inv_component = True
                    elif p.isdigit() and len(p) > 2:
                        if len(current['inv_str']) > 0:
                            is_inv_component = True
                    elif re.match(r'^[Pp]\d{7}$', p):
                        # P1124103 pattern - part of second invoice
                        is_inv_component = True
                    
                    if is_inv_component:
                        current['inv_str'] += (' ' + p if current['inv_str'] else p)
                    elif MEMBER_NO_RE.match(p):
                        current['member_no'] = p
                        current['_name_collected'] = True  # Stop collecting name
                    elif AMOUNT_RE.match(p):
                        current['amounts'].append(p)
                    else:
                        # Only add to name_parts if not already collected from date line
                        if not current.get('_name_collected'):
                            current['name_parts'].append(p)
                
                amt_match = re.search(r'(\d+\.\d{3})\s+(\d+\.\d{3})\s+(\d+\.\d{3})\s+(\d+\.\d{3})\s+(\d+\.\d{3})\s+(\d+\.\d{3})\s+(\d+\.\d{3})\s+(\d+\.\d{3})\s+(\d+)', line)
                if amt_match:
                    current['amounts'] = list(amt_match.groups())[:-1]
                    current['is_complete'] = True
        
        if current and current.get('amounts') and current.get('inv_str'):
            records.append(current)

        rows = []
        for r in records:
            inv_str = r['inv_str']
            
            raw_tokens = re.split(r'[\s/]+', inv_str)
            
            potential_invoices = []
            base_prefix = ''
            
            for token in raw_tokens:
                if not token: continue
                
                if INV_PREFIX_RE.match(token):
                    base_prefix = token[:7]
                
                if INV_STRICT_RE.match(token):
                    potential_invoices.append(token)
                elif token.isdigit():
                    if base_prefix:
                        if len(base_prefix) + len(token) == 12:
                            potential_invoices.append(base_prefix + token)
                        elif len(base_prefix) == 7 and len(token) == 5:
                            potential_invoices.append(base_prefix + token)
                        elif len(token) == 12:
                            potential_invoices.append(token)
            
            if not potential_invoices:
                all_matches = re.findall(r'(?:AOP|AIP|BOP|COP|HSP|RSP)\d{9}', inv_str, re.I)
                potential_invoices = all_matches if all_matches else []
            
            if len(potential_invoices) == 1:
                # Try to find second invoice from P1124XXX + 2-digit combination
                p_matches = re.findall(r'[Pp](\d{7})', inv_str)
                two_digit_tokens = re.findall(r'\b(\d{2})\b', inv_str)
                
                if p_matches and two_digit_tokens:
                    base_prefix = potential_invoices[0][:7]
                    p_digit = p_matches[0]
                    two_digit = two_digit_tokens[-1]
                    middle = p_digit[-3:]
                    second_suffix = middle + two_digit
                    second_inv = base_prefix + second_suffix
                    if len(second_inv) == 12:
                        potential_invoices.append(second_inv)
            
            if not potential_invoices:
                clean_inv = inv_str.replace('/', '').replace(' ', '')
                if len(clean_inv) >= 12:
                    prefix_match = re.match(r'^(AOP|AIP|BOP|COP|HSP|RSP)\d{4}', clean_inv, re.I)
                    if prefix_match:
                        prefix = prefix_match.group()[:7]
                        remaining = clean_inv[len(prefix):]
                        if len(remaining) >= 5:
                            potential_invoices = [prefix + remaining[:5]]
            
            if not potential_invoices:
                clean_inv = inv_str.replace('/', '').replace(' ', '')
                if len(clean_inv) >= 12:
                    prefix_match = re.match(r'^(AOP|AIP|BOP|COP|HSP|RSP)', clean_inv, re.I)
                    if prefix_match:
                        prefix = prefix_match.group()
                        digits = clean_inv[len(prefix):]
                        if len(digits) >= 9:
                            potential_invoices = [prefix + digits[:9]]
            
            for i, inv in enumerate(potential_invoices):
                amts = r['amounts'] if i == 0 else ['0.000'] * 10
                remark_str = ', '.join(r['remarks'])
                
                def get_amt(idx):
                    val = amts[idx] if idx < len(amts) else '0.000'
                    return val.replace(',', '')

                rows.append((
                    r['date'],
                    inv,
                    r['pat_id'],
                    ' '.join(r['name_parts']),
                    r['member_no'],
                    get_amt(0),
                    get_amt(1),
                    get_amt(2),
                    get_amt(3),
                    get_amt(4),
                    get_amt(5),
                    get_amt(6),
                    get_amt(7),
                    remark_str
                ))
        
        return rows

    def transform(self, raw_data):
        formatted_rows = []
        sl_no_counter = 1

        for row in raw_data:
            # Columns: date, inv, pat_id, name, mem_no, cols...
            date = row[0]
            inv = row[1].upper()
            pat_id = row[2]
            name = row[3]
            mem_no = row[4]
            net_payment = row[11]
            amt_to_adjust = row[11]
            gems_remark = row[13]

            if not inv:
                continue

            new_row = [
                sl_no_counter,
                inv,
                date,
                pat_id,
                name,
                net_payment,
                amt_to_adjust,
                mem_no,
                gems_remark,
                '',
                ''
            ]
            
            formatted_rows.append(new_row)
            sl_no_counter += 1
        
        return self.formatted_headers, formatted_rows
