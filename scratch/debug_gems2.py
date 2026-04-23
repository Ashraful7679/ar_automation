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

# Trace lines 66-70 (0-indexed: 65-69)
current = None
last_prefix = None
last_date = None
records = []

for i in range(65, 71):
    line = all_lines[i].strip()
    print('=== Line ' + str(i) + ': ' + line[:50])
    
    # Check invoice start FIRST
    if current and current.get('amounts'):
        inv_start = INVOICE_START_RE.match(line)
        if inv_start:
            inv_clean = current['inv_str'].replace('/', '').replace(' ', '')
            print(f'  inv_start detected, current inv_clean length: {len(inv_clean)}')
            
            if len(inv_clean) >= 12:
                print('  Current complete, saving prev and creating new')
                records.append(current)
            else:
                print('  Current incomplete, treating as continuation')
            
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
            
            print('  New record inv_str: ' + current['inv_str'])
            continue
        
        cont = CONTINUATION_RE.match(line)
        if cont:
            print('  Continuation')
            continue
    
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    if date_match:
        print('  Date line')
        # Save previous
        if current and current.get('amounts') and current.get('inv_str'):
            records.append(current)
            print('  Saved prev record')
        
        last_date = date_match.group()
        
        # Get prefix
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
        
        print('  New current: inv_str=' + current['inv_str'] + ', amounts=' + str(len(current['amounts'])))
        continue
    
    # OTHER section
    print('  OTHER section')
    if current and not current.get('amounts'):
        parts = line.split()
        print(f'    Parts: {parts}')
        for p in parts:
            is_inv_component = False
            if INV_PREFIX_RE.search(p):
                is_inv_component = True
            elif '/' in p:
                is_inv_component = True
            elif p.isdigit() and len(p) > 2:
                if len(current['inv_str']) > 0:
                    is_inv_component = True
            
            print(f'    Token: {p}, is_inv_component: {is_inv_component}')
            
            if is_inv_component:
                current['inv_str'] += (' ' + p if current['inv_str'] else p)
            elif MEMBER_NO_RE.match(p):
                current['member_no'] = p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
            else:
                current['name_parts'].append(p)
        
        print('    After processing: inv_str=' + current['inv_str'])
    else:
        print('    Skipped (no current or has amounts)')
