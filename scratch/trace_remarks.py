import pdfplumber
import re

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')

with pdfplumber.open('uploads/3493 GEMS.pdf') as pdf:
    all_text = ''
    for page in pdf.pages:
        all_text += page.extract_text() + '\n'
    lines = all_text.split('\n')

# Trace through lines 85-95
current = None
records = []
last_prefix = None
last_date = None

for i in range(85, 96):
    line = lines[i].strip()
    print(f'=== Line {i}: {line[:50]}')
    
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    
    if date_match:
        print('  -> Date line')
        # Check if data line
        parts = line.split()
        has_data_token = False
        if len(parts) > 1:
            for p in parts[1:]:
                if INV_PREFIX_RE.match(p) or p.isdigit():
                    has_data_token = True
                    break
        
        if not has_data_token:
            print('  -> Not data line')
            continue
        
        # Save previous
        if current and current.get('amounts') and current.get('inv_str'):
            records.append(current)
            print(f'  -> Saved record: inv={current.get("inv_str")}, remarks={current.get("remarks", [])}')
        
        last_date = date_match.group()
        
        for p in line.split()[1:]:
            if INV_PREFIX_RE.match(p):
                last_prefix = p[:7]
                print(f'  -> Prefix: {last_prefix}')
                break
        
        current = {'date': last_date, 'inv_str': '', 'amounts': [], 'remarks': []}
        
        parts = line.split()
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                current['inv_str'] += p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                print(f'  -> Amount found: {p}')
                break
        
        print(f'  -> New current: inv_str={current["inv_str"]}')
        continue
    
    # Check for Remarks
    if line.startswith('Remarks :') or line.startswith('/'):
        print('  -> Remarks')
        if current:
            current['remarks'].append(line.replace('Remarks :', '').strip())
            print(f'  -> Added remark. Total: {len(current.get("remarks", []))}')
        continue
    
    print('  -> Other')

print()
print('Final records:')
for r in records:
    print(f'  inv={r.get("inv_str")}, remarks={r.get("remarks", [])}')
