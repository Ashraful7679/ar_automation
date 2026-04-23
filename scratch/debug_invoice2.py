import re

INV_PREFIX_RE = re.compile(r'^(AOP|AIP|BOP|COP|HSP|RSP)', re.IGNORECASE)
INV_STRICT_RE = re.compile(r'^(?:AOP|AIP|BOP|COP|HSP|RSP)\d{9}$', re.IGNORECASE)

# Test the invoice parsing logic
inv_str = 'AOP112410330/AO P1124103 50'

print('inv_str:', inv_str)

# Try to extract both invoices
# Current logic
raw_tokens = re.split(r'[\s/]+', inv_str)
print('raw_tokens:', raw_tokens)

potential_invoices = []
base_prefix = ''

for token in raw_tokens:
    if not token:
        continue
    
    if INV_PREFIX_RE.match(token):
        base_prefix = token[:7]
        print(f'Prefix: {base_prefix}')
    
    # Check strict
    if INV_STRICT_RE.match(token):
        print(f'Strict match: {token}')
        potential_invoices.append(token)
    elif token.isdigit():
        if base_prefix:
            if len(base_prefix) + len(token) == 12:
                print(f'Digit combine (12): {base_prefix + token}')
                potential_invoices.append(base_prefix + token)
            elif len(base_prefix) == 7 and len(token) == 5:
                print(f'Digit combine (5): {base_prefix + token}')
                potential_invoices.append(base_prefix + token)

# New logic: handle P1124103 type tokens
# These need to be converted: P1124103 -> 10350 (by removing P prefix and taking last 5 digits)
# Then combine with base_prefix to form invoice

print()
print('=== NEW LOGIC ===')
# Look for patterns like P1124XXX (P prefix + 9 digits)
p_pattern = re.findall(r'[Pp](\d{7})', inv_str)
print('P-pattern matches:', p_pattern)

for p_digit in p_pattern:
    # P + 7 digits: e.g., P1124103
    # We want to extract last 5 digits: 4103 -> wait, that's 4 digits
    # P1124103: digits are 1124103 (7 digits)
    # Taking last 5: 24103
    suffix = p_digit[2:]  # Last 5 digits of the 7-digit string
    if base_prefix and len(suffix) == 5:
        inv = base_prefix + suffix
        print(f'P-derived invoice: {inv}')
        potential_invoices.append(inv)

# Also check for 2-digit suffixes after invoice patterns
# Look for patterns like ...XX at end (2 digits)
two_digit_match = re.search(r'(\d{2})$', inv_str)
print('Two digit suffix:', two_digit_match.group(1) if two_digit_match else None)

print()
print('Final potential invoices:', potential_invoices)
