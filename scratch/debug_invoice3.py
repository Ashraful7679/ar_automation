import re

# More careful analysis of the 2-invoice case
# From the PDF:
# Line 67: 10330/AO Abdulwahab Matar
# Line 68: P1124103
# Line 69: 50
# 
# Combined: AOP1124 10330/AO P1124103 50
# 
# Expected:
# Invoice 1: AOP1124 + 10330 = AOP112410330
# Invoice 2: AOP1124 + 10350 = AOP112410350

# Let's see:
# - "10330" from line 67 -> first invoice suffix
# - "P1124103" and "50" from lines 68-69 -> second invoice suffix
#   - P1124103 -> digits "1124103" 
#   - Taking last 3 digits "103" and combining with "50" from next line -> "10350"

# So the logic is:
# 1. Extract first 5-digit suffix: 10330
# 2. Extract second 5-digit suffix: P1124103 + 50 -> last 3 digits of 1124103 (103) + 50 = 10350

inv_str = 'AOP112410330/AO P1124103 50'
print('Testing inv_str:', inv_str)

potential_invoices = []

# Current: strict match finds AOP112410330
INV_STRICT_RE = re.compile(r'^(?:AOP|AIP|BOP|COP|HSP|RSP)\d{9}$', re.IGNORECASE)
strict_match = INV_STRICT_RE.match(inv_str)
if strict_match:
    potential_invoices.append(strict_match.group())
    print('Found strict:', strict_match.group())

# For second invoice:
# Look for patterns like P1124XXX where XXX is 3 digits
# Then combine with following 2-digit suffix

# Find all P + 7-digit patterns
p_matches = re.findall(r'[Pp](\d{7})', inv_str)
print('P matches:', p_matches)

# Find 2-digit suffix
two_digit = re.findall(r'\s(\d{2})$', inv_str)
print('Two digit:', two_digit)

# If we have P1124103 and 50:
# - Take last 3 digits of 1124103 = 103
# - Add 50 = 10350
# - Prepend base prefix: AOP1124 + 10350 = AOP112410350

if p_matches and two_digit:
    p_digit = p_matches[0]  # '1124103'
    suffix_2dig = two_digit[0]  # '50'
    # Last 3 of the 7-digit P-part + the 2-digit
    middle = p_digit[-3:]  # '103'
    suffix_2 = middle + suffix_2dig  # '10350'
    print('Second suffix:', suffix_2)
    base_prefix = 'AOP1124'
    potential_invoices.append(base_prefix + suffix_2)
    print('Second invoice:', base_prefix + suffix_2)

print()
print('Final:', potential_invoices)
