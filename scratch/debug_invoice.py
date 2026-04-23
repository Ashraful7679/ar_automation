import re

INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
INV_STRICT_RE = re.compile(r'^(?:AOP|AIP|BOP|COP|HSP|RSP)\d{9}$', re.IGNORECASE)

# Test case: inv_str from record 66-67
inv_str = 'AOP112410330/AO'

print('inv_str:', inv_str)

raw_tokens = re.split(r'[\s/]+', inv_str)
print('raw_tokens:', raw_tokens)

potential_invoices = []
base_prefix = ''

for token in raw_tokens:
    if not token: continue
    
    if INV_PREFIX_RE.match(token):
        base_prefix = token[:7]
        print(f'Found prefix: {base_prefix}')
    
    if INV_STRICT_RE.match(token):
        print(f'Found strict: {token}')
        potential_invoices.append(token)
    elif token.isdigit():
        print(f'Checking digit: {token} with prefix {base_prefix}')
        if base_prefix:
            if len(base_prefix) + len(token) == 12:
                print(f'  -> Adding: {base_prefix + token}')
                potential_invoices.append(base_prefix + token)
            elif len(base_prefix) == 7 and len(token) == 5:
                print(f'  -> Adding: {base_prefix + token}')
                potential_invoices.append(base_prefix + token)

print('potential_invoices:', potential_invoices)

# Check regex findall
all_matches = re.findall(r'(?:AOP|AIP|BOP|COP|HSP|RSP)\d{9}', inv_str, re.I)
print('regex findall:', all_matches)
