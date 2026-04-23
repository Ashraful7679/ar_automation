import pdfplumber
import re

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
INVOICE_START_RE = re.compile(r'^(\d{5})(/[A-Z]{1,3})')
CONTINUATION_RE = re.compile(r'^(\d{3,5})(?:\s+[A-Za-z].*)?$')
NOISE_RE = re.compile(r'\d{2}/\d{2}/\d{4}\d+')
MEMBER_NO_RE = re.compile(r'^\d+-\d+$')

all_lines = []
with pdfplumber.open('uploads/3493 GEMS.pdf') as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text: all_lines.extend(text.split('\n'))

# Trace lines 66-70 more carefully
current = None
last_prefix = None
last_date = None

for i in range(65, 71):
    line = all_lines[i].strip()
    print('=== Line ' + str(i) + ': ' + line)
    
    if current and current.get('amounts'):
        inv_start = INVOICE_START_RE.match(line)
        if inv_start:
            inv_clean = current['inv_str'].replace('/', '').replace(' ', '')
            print('  inv_start, inv_clean: ' + inv_clean)
            
            if len(inv_clean) >= 12:
                print('  Complete, saving')
            else:
                print('  Incomplete, appending')
                digits = inv_start.group(1)
                suffix = inv_start.group(2)
                needed = 12 - len(inv_clean)
                if needed > 0:
                    current['inv_str'] += digits[:needed]
                    if suffix:
                        current['inv_str'] += suffix
                print('  After append: ' + current['inv_str'])
            
            # Create new record - but also append to current!
            digits = inv_start.group(1)
            suffix = inv_start.group(2)
            
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
            
            print('  New current: ' + current['inv_str'])
            continue
        
        cont = CONTINUATION_RE.match(line)
        if cont:
            print('  Continuation')
            continue
    
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    if date_match:
        print('  Date')
        last_date = date_match.group()
        
        for p in line.split()[1:]:
            if INV_PREFIX_RE.match(p):
                last_prefix = p[:7]
                break
        
        current = {'date': last_date, 'inv_str': '', 'amounts': [], 'name_parts': []}
        
        parts = line.split()
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                current['inv_str'] += p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                break
        
        print('  New: ' + current['inv_str'])
        continue
    
    # OTHER
    print('  OTHER, has amounts:', bool(current and current.get('amounts')))
    if current and current.get('amounts'):
        parts = line.split()
        for p in parts:
            is_inv = INV_PREFIX_RE.search(p) or '/' in p or (p.isdigit() and len(p) > 2 and current.get('inv_str'))
            if is_inv:
                current['inv_str'] += (' ' + p if current['inv_str'] else p)
                print('    Added to inv: ' + p + ' -> ' + current['inv_str'])
            elif MEMBER_NO_RE.match(p):
                current['member_no'] = p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
            else:
                current['name_parts'].append(p)
