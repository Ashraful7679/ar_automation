import re

INV_STRICT_RE = re.compile(r'^(?:AOP|AIP|BOP|COP|HSP|RSP)\d{9}$', re.IGNORECASE)

inv_str = 'AOP112410330/AO P1124103 50'

potential_invoices = []

# Check strict matches first
raw_tokens = re.split(r'[\s/]+', inv_str)
for token in raw_tokens:
    if INV_STRICT_RE.match(token):
        print('Strict match:', token)
        potential_invoices.append(token)

print('Initial potential_invoices:', potential_invoices)
print('Length:', len(potential_invoices))

# Second invoice logic
if len(potential_invoices) == 1:
    print('Running second invoice logic...')
    p_matches = re.findall(r'[Pp](\d{7})', inv_str)
    two_digit_match = re.search(r'\s(\d{2})\s*$', inv_str)
    print('P matches:', p_matches)
    print('Two digit:', two_digit_match.group(1) if two_digit_match else None)
    
    if p_matches and two_digit_match:
        base_prefix = potential_invoices[0][:7]
        p_digit = p_matches[0]
        two_digit = two_digit_match.group(1)
        middle = p_digit[-3:]
        second_suffix = middle + two_digit
        second_inv = base_prefix + second_suffix
        print('Second suffix:', second_suffix)
        print('Second invoice:', second_inv)
        if len(second_inv) == 12:
            potential_invoices.append(second_inv)

print('Final potential_invoices:', potential_invoices)
