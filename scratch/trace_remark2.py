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

# Trace around lines 90-95
current = None
last_prefix = None
last_date = None
records = []

for i in range(88, 96):
    line = all_lines[i].strip()
    print(f'=== Line {i}: {line[:50]}')
    
    if not line: continue
    
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
            continue
        
        cont_match = CONTINUATION_RE.match(line)
        if cont_match and needs_more:
            digits = cont_match.group(1)
            inv_clean2 = current['inv_str'].replace('/', '').replace(' ', '')
            needed = 12 - len(inv_clean2)
            if needed > 0:
                current['inv_str'] += digits[:needed]
            continue
    
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    
    if date_match:
        print(f'  DATE LINE, last_date={last_date}')
        parts = line.split()
        has_data_token = any(INV_PREFIX_RE.match(p) or p.isdigit() for p in parts[1:])
        
        if not has_data_token: continue
        
        # Save previous
        if current and current.get('amounts') and current.get('inv_str'):
            records.append(current)
            print(f'  SAVED: inv={current["inv_str"]}, remarks={current.get("remarks", [])}')
        
        last_date = date_match.group()
        
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                last_prefix = p[:7]
        
        current = {'date': last_date, 'inv_str': '', 'amounts': [], 'remarks': [], 'name_parts': [], '_name_collected': False}
        
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p): current['inv_str'] += p
            elif p.isdigit() and current['inv_str']:
                inv_c = current['inv_str'].replace('/', '').replace(' ', '')
                if len(inv_c) < 7: current['inv_str'] += p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                current['_name_collected'] = True
            elif not (INV_PREFIX_RE.match(p) or p.isdigit() or '/' in p):
                if not current.get('_name_collected'): current['name_parts'].append(p)
        
        print(f'  NEW: inv={current["inv_str"]}, remarks={current.get("remarks", [])}')
        continue
    
    # Remark handling
    if line.startswith('Remarks :') or line.startswith('/'):
        current['remarks'].append(line.replace('Remarks :', '').strip())
        print(f'  REMARK: {current["remarks"]}')
        continue
    
    print('  OTHER')
