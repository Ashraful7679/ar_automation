import pdfplumber
import re

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
CONTINUATION_RE = re.compile(r'^(\d{3,5})(?:\s+[A-Za-z].*)?$')
INVOICE_START_RE = re.compile(r'^(\d{5})(/[A-Z]{1,3})')

with pdfplumber.open('uploads/3493 GEMS.pdf') as pdf:
    all_text = ''
    for page in pdf.pages:
        all_text += page.extract_text() + '\n'
    lines = all_text.split('\n')

# Trace lines 88-93 where AIP112400302 is
current = None
records = []
last_prefix = None
last_date = None

for i in range(88, 94):
    line = lines[i].strip()
    print(f'=== Line {i}: {line[:55]}')
    
    # Check invoice continuation first
    if current:
        inv_clean = re.sub(r'[^A-Za-z0-9]', '', current.get('inv_str', ''))
        needs_more = len(inv_clean) < 12
        
        inv_start_match = INVOICE_START_RE.match(line)
        if inv_start_match and needs_more:
            digits = inv_start_match.group(1)
            suffix = inv_start_match.group(2)
            inv_clean2 = current['inv_str'].replace('/', '').replace(' ', '')
            needed = 12 - len(inv_clean2)
            if needed > 0:
                current['inv_str'] += digits[:needed]
                if suffix:
                    current['inv_str'] += suffix
            rest = line[len(digits + (suffix or '')):].strip()
            if rest:
                current['name_parts'].extend(rest.split())
            print(f'  -> inv_start incomplete: {current["inv_str"]}')
            continue
        
        cont_match = CONTINUATION_RE.match(line)
        if cont_match and needs_more:
            digits = cont_match.group(1)
            inv_clean2 = current['inv_str'].replace('/', '').replace(' ', '')
            needed = 12 - len(inv_clean2)
            if needed > 0:
                current['inv_str'] += digits[:needed]
            print(f'  -> continuation: {current["inv_str"]}')
            continue
    
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    
    if date_match:
        print('  -> Date line')
        parts = line.split()
        has_data_token = False
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p) or p.isdigit():
                has_data_token = True
                break
        
        if not has_data_token:
            continue
        
        # Save previous
        if current and current.get('amounts') and current.get('inv_str'):
            records.append(current)
            print(f'  -> Saved: inv={current["inv_str"]}, remarks={current.get("remarks", [])}')
        
        last_date = date_match.group()
        
        for p in line.split()[1:]:
            if INV_PREFIX_RE.match(p):
                last_prefix = p[:7]
                print(f'  -> last_prefix: {last_prefix}')
                break
        
        current = {'date': last_date, 'inv_str': '', 'amounts': [], 'remarks': []}
        
        parts = line.split()
        skipped_digits = ''
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                current['inv_str'] += p
            elif p.isdigit():
                if current['inv_str']:
                    inv_c = current['inv_str'].replace('/', '').replace(' ', '')
                    if len(inv_c) < 7:
                        current['inv_str'] += p
                    else:
                        skipped_digits += p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                break
        
        print(f'  -> New current: inv_str={current["inv_str"]}, skipped={skipped_digits}')
        continue
    
    if line.startswith('Remarks :') or line.startswith('/'):
        if current:
            current['remarks'].append(line.replace('Remarks :', '').strip())
            print(f'  -> Added remark')
        continue
    
    print('  -> Other')
