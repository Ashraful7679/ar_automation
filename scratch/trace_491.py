import pdfplumber
import re

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
MEMBER_NO_RE = re.compile(r'^\d+-\d+$')
INVOICE_START_RE = re.compile(r'^(\d{5})(/[A-Z]{1,3})')
CONTINUATION_RE = re.compile(r'^(\d{3,5})(?:\s+[A-Za-z].*)?$')

all_lines = []
with pdfplumber.open('uploads/3493 GEMS.pdf') as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text: all_lines.extend(text.split('\n'))

# Trace around line 80-85
current = None
last_prefix = None
last_date = None
records = []

for i in range(78, 86):
    line = all_lines[i].strip()
    print('Line ' + str(i) + ': ' + line[:50])
    
    if current:
        inv_clean = re.sub(r'[^A-Za-z0-9]', '', current.get('inv_str', ''))
        needs_more = len(inv_clean) < 12
        
        inv_start = INVOICE_START_RE.match(line)
        if inv_start and needs_more:
            print('  inv_start')
            continue
        
        cont = CONTINUATION_RE.match(line)
        if cont and needs_more:
            print('  continuation')
            continue
    
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    if date_match:
        parts = line.split()
        has_data = any(INV_PREFIX_RE.match(p) or p.isdigit() for p in parts[1:])
        if not has_data: continue
        
        if current and current.get('amounts') and current.get('inv_str'):
            records.append(current)
            print('  SAVED: ' + current.get('inv_str', '') + ' names: ' + str(current.get('name_parts', [])))
        
        last_date = date_match.group()
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                last_prefix = p[:7]
        
        current = {'date': last_date, 'inv_str': '', 'amounts': [], 'name_parts': [], '_name_collected': False}
        
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                current['inv_str'] += p
            elif p.isdigit():
                if current['inv_str']:
                    inv_c = current['inv_str'].replace('/', '').replace(' ', '')
                    if len(inv_c) < 7:
                        current['inv_str'] += p
            elif MEMBER_NO_RE.match(p):
                current['member_no'] = p
                current['_name_collected'] = True
                print('  Member no: ' + p)
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                current['_name_collected'] = True
            elif not (INV_PREFIX_RE.match(p) or p.isdigit() or '/' in p):
                if not current.get('_name_collected'):
                    current['name_parts'].append(p)
        
        print('  Date line: names: ' + str(current['name_parts']))
        continue
    
    if line.startswith('Remarks :') or line.startswith('/'):
        continue
    
    print('  OTHER')
