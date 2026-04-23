import sys
sys.path.insert(0, 'E:/Completed Projects/AR_Automation')

# Debug: trace the exact record for AIP112400302
import pdfplumber
import re
from parsers.gems import GemsParser

# Parse and look at the specific record
p = GemsParser()

# Add debug prints to the invoice parsing step
# Let me trace what happens with inv_str='AIP112400302' during parsing

INV_STRICT_RE = re.compile(r'^(?:AOP|AIP|BOP|COP|HSP|RSP)\d{9}$', re.IGNORECASE)

# Test case: inv_str = 'AIP112400302' with no P-pattern, just the single invoice
inv_str = 'AIP112400302'
print('Testing inv_str:', inv_str)

# Current logic
raw_tokens = re.split(r'[\s/]+', inv_str)
print('Raw tokens:', raw_tokens)

potential_invoices = []
base_prefix = ''

for token in raw_tokens:
    if not token: continue
    
    if re.match(r'^(AOP|AIP|BOP|COP|HSP|RSP)', token, re.I):
        base_prefix = token[:7]
        print(f'  Found prefix: {base_prefix}')
    
    if INV_STRICT_RE.match(token):
        print(f'  Strict match: {token}')
        potential_invoices.append(token)
    elif token.isdigit():
        if base_prefix:
            if len(base_prefix) + len(token) == 12:
                potential_invoices.append(base_prefix + token)
                print(f'  Combined: {base_prefix + token}')

print('Potential invoices:', potential_invoices)
