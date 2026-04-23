import pdfplumber
import re

pdf = pdfplumber.open('uploads/3493 GEMS.pdf')
all_lines = []
for page in pdf.pages:
    text = page.extract_text()
    if text:
        all_lines.extend(text.split('\n'))

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
PAT_FILE_RE = re.compile(r'^\d{5,6}$')

current = None
records = []

for line in all_lines:
    line = line.strip()
    if not line: continue
    
    parts = line.split()
    if not parts: continue
    
    date_match = DATE_RE.match(parts[0])
    
    if date_match:
        if current:
            records.append(current)
        
        current = {'pat_id': '', 'inv_str': '', 'name_parts': [], 'amounts': []}
        
        for p in parts[1:]:
            if PAT_FILE_RE.match(p) and not current['pat_id']:
                current['pat_id'] = p
            elif AMOUNT_RE.match(p):
                current['amounts'].append(p)
                break
            else:
                current['inv_str'] += p

if current:
    records.append(current)

print('Total records:', len(records))
for r in records[:5]:
    print(f'inv={r["inv_str"][:20]}, pat_id={r["pat_id"]}')