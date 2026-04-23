import pdfplumber
import re

AMOUNT_RE = re.compile(r'^[\d,]+\.\d{2,3}$')
DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')

with pdfplumber.open('uploads/3493 GEMS.pdf') as pdf:
    all_text = ''
    for page in pdf.pages:
        all_text += page.extract_text() + '\n'
    lines = all_text.split('\n')

# Look at lines around 88-95
for i in range(88, 96):
    line = lines[i]
    date_match = DATE_RE.match(line.split()[0]) if line.split() else None
    
    # Check amount pattern
    parts = line.split()
    amounts_found = []
    for p in parts:
        if AMOUNT_RE.match(p):
            amounts_found.append(p)
    
    print(f'Line {i}: {line[:60]}')
    print(f'  Date match: {bool(date_match)}, Amounts: {amounts_found}')
