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
        if text: all_lines.extend(text.split('\n'))

# Trace around line 45-50 where SAFA is
current = None
last_prefix = None
last_date = None

for i in range(44, 52):
    line = all_lines[i].strip()
    print(f'=== Line {i}: {line[:55]}')
    
    if current:
        inv_clean = re.sub(r'[^A-Za-z0-9]', '', current.get('inv_str', ''))
        needs_more = len(inv_clean) < 12
        
        print(f'  Current: inv={current.get("inv_str")}, needs_more={needs_more}')
        
        inv_start = INVOICE_START_RE.match(line)
        if inv_start and needs_more:
            print('  -> inv_start incomplete, continuing')
            continue
        
        cont = CONTINUATION_RE.match(line)
        if cont and needs_more:
            print('  -> continuation')
            continue
    
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    if date_match:
        print('  -> DATE LINE')
        parts = line.split()
        has_data = any(INV_PREFIX_RE.match(p) or p.isdigit() for p in parts[1:])
        if not has_data:
            print('  -> Not data line')
            continue
        
        if current and current.get('amounts') and current.get('inv_str'):
            print(f'  -> Saved prev: inv={current.get("inv_str")}, names={current.get("name_parts")}')
        
        last_date = date_match.group()
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                last_prefix = p[:7]
        
        current = {'date': last_date, 'inv_str': '', 'amounts': [], 'name_parts': [], '_name_collected': False}
        
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                current['inv_str'] += p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                current['_name_collected'] = True
                break
            elif not (INV_PREFIX_RE.match(p) or p.isdigit() or '/' in p):
                if not current.get('_name_collected'):
                    current['name_parts'].append(p)
        
        print(f'  -> New: inv={current["inv_str"]}, names={current["name_parts"]}, collected={current["_name_collected"]}')
        continue
    
    print('  -> OTHER')
    if current and current.get('amounts'):
        parts = line.split()
        for p in parts:
            if not current.get('_name_collected'):
                current['name_parts'].append(p)
        print(f'    Added names: {current["name_parts"]}')
