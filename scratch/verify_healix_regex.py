import re

text = """
06/09/2023 INV AOP082309428 Zachariah Ahmad Ian Doyle Jam
26.72 0.00 26.72 0.00
06/09/2023 INV AOP082308983 Alastair Long, Unknown 35.40 0.00 35.40 0.00
06/09/2023 INV AOP082307079 Zachariah Ahmad Ian Doyle Jam 52.68 0.00 52.68 0.00
06/09/2023 INV AOP082306455 Catherine Rodrigues, Unknown 129.00 0.00 129.00 0.00
"""

# Simulate joining
lines = text.strip().split('\n')
joined_lines = []
current_line = ""
for line in lines:
    if re.search(r'\d{2}/\d{2}/\d{4}', line):
        if current_line: joined_lines.append(current_line)
        current_line = line
    else:
        current_line += " " + line
if current_line: joined_lines.append(current_line)

pattern = re.compile(
    r'(?P<date>\d{2}/\d{2}/\d{4})\s+'
    r'(?P<type>INV)\s+'
    r'(?P<ref>[A-Z]{3}\d{6,})\s+'
    r'(?P<desc>.+?)\s+'
    r'(?P<debit>[\d,\.]+)\s+'
    r'(?P<credit>[\d,\.]+)\s+'
    r'(?P<remitted>[\d,\.]+)'
)

total_remitted = 0
for line in joined_lines:
    match = pattern.search(line)
    if match:
        rem = float(match.group('remitted'))
        total_remitted += rem
        print(f"Matched: {match.group('ref')} -> {rem}")
    else:
        print(f"Failed to match: {line}")

print(f"Total Remitted: {total_remitted}")
