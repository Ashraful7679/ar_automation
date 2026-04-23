import sys
sys.path.insert(0, 'E:/Completed Projects/AR_Automation')

# Import raw parsing to see inv_str
import pdfplumber
import re
from parsers.gems import GemsParser

# Quick debug: check what the parser produces for the record with date 16/11/2024
p = GemsParser()
rows = p.parse('uploads/3493 GEMS.pdf')

# Find the row with date 16/11/2024 and check what invoice it has
for row in rows:
    if row[0] == '16/11/2024':
        print(f'Inv: {row[1]}, PatID: {row[2]}, Remarks: {row[13][:50]}...')

# Now check what happens in the raw parsing
print()
print('=== Checking raw inv_str for 16/11/2024 date line ===')

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
CONTINUATION_RE = re.compile(r'^(\d{3,5})(?:\s+[A-Za-z].*)?$')
INVOICE_START_RE = re.compile(r'^(\d{5})(/[A-Z]{1,3})')

all_lines = []
with pdfplumber.open('uploads/3493 GEMS.pdf') as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text: all_lines.extend(text.split('\n'))

current = None
last_prefix = None
last_date = None

for i, line in enumerate(all_lines):
    line = line.strip()
    if not line: continue
    
    # Check for inv continuation first
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
            if current['date'] == '16/11/2024':
                print(f'  Previous record saved with date {last_date}')
                print(f'    inv_str: {current.get("inv_str")}')
                print(f'    remarks: {current.get("remarks", [])}')
        
        last_date = date_match.group()
        
        for p in line.split()[1:]:
            if INV_PREFIX_RE.match(p):
                last_prefix = p[:7]
                break
        
        current = {'date': last_date, 'inv_str': '', 'amounts': [], 'remarks': [], 'name_parts': []}
        
        parts = line.split()
        for p in parts[1:]:
            if INV_PREFIX_RE.match(p):
                current['inv_str'] += p
            elif p.isdigit() and current['inv_str']:
                inv_c = current['inv_str'].replace('/', '').replace(' ', '')
                if len(inv_c) < 7:
                    current['inv_str'] += p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                break
        
        if last_date == '16/11/2024':
            print(f'Date line 16/11/2024: inv_str after processing = {current["inv_str"]}')
        
        continue
    
    if line.startswith('Remarks :') or line.startswith('/'):
        if current:
            current['remarks'].append(line.replace('Remarks :', '').strip())
            if current.get('date') == '16/11/2024':
                print(f'  Added remark to record with date 16/11/2024')
        continue
