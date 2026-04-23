import pdfplumber
import re

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
INVOICE_START_RE = re.compile(r'^(\d{5})(/[A-Z]{1,3})')
CONTINUATION_RE = re.compile(r'^(\d{3,5})(?:\s+[A-Za-z].*)?$')

all_lines = []
with pdfplumber.open('uploads/3493 GEMS.pdf') as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text: 
            all_lines.extend(text.split('\n'))

current = None
last_prefix = None
last_date = None
record_count = 0

for i in range(63, 73):
    line = all_lines[i].strip()
    
    if current and current.get('amounts'):
        inv_start = INVOICE_START_RE.match(line)
        if inv_start:
            record_count += 1
            print(f'Line {i}: SAVING RECORD #{record_count}: {current.get("inv_str")}')
            print(f'  -> Starting new with: {inv_start.group(1)}{inv_start.group(2)}')
            current = {
                'date': last_date,
                'inv_str': inv_start.group(1) + inv_start.group(2),
                'pat_id': '',
                'name_parts': [],
                'member_no': '',
                'amounts': [],
                'remarks': [],
                'is_complete': False
            }
            if last_prefix:
                current['inv_str'] = last_prefix + current['inv_str']
            print(f'  -> New inv_str: {current["inv_str"]}')
            continue
        
        cont = CONTINUATION_RE.match(line)
        if cont:
            digits = cont.group(1)
            inv_clean = current['inv_str'].replace('/', '').replace(' ', '')
            needed = 12 - len(inv_clean)
            if needed > 0:
                current['inv_str'] += digits[:needed]
            print(f'Line {i}: CONTINUATION {digits} -> inv_str: {current["inv_str"]}')
            continue
    
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    if date_match:
        last_date = date_match.group()
        
        # Get prefix
        for p in line.split()[1:]:
            if INV_PREFIX_RE.match(p):
                last_prefix = p[:7]
                break
        
        if current and current.get('amounts') and current.get('inv_str'):
            record_count += 1
            print(f'Line {i}: SAVING PREVIOUS #{record_count}: {current.get("inv_str")}')
        
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
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                current['inv_str'] += p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                break
        
        print(f'Line {i}: DATE {last_date} -> inv_str: {current["inv_str"]}, amounts: {len(current["amounts"])}')
        continue
    
    print(f'Line {i}: OTHER: {line[:50]}')
