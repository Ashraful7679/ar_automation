from parsers.gems import GemsParser
p = GemsParser()
rows = p.parse('uploads/3493 GEMS.pdf')

print('=== Checking 09424 and 09453 invoices ===')
for i, row in enumerate(rows):
    if '09424' in row[1] or '09453' in row[1]:
        print(f'{i+1}. Inv: {row[1]}')

print()
print('=== Checking 10330 and 10350 invoices ===')
for i, row in enumerate(rows):
    if '10330' in row[1] or '10350' in row[1]:
        print(f'{i+1}. Inv: {row[1]}')

print()
print('=== AIP112400302 remarks ===')
for i, row in enumerate(rows):
    if 'AIP112400302' in row[1]:
        print(row[13])

print()
print('=== AOP112409424 remarks ===')
for i, row in enumerate(rows):
    if 'AOP112409424' in row[1]:
        print(row[13])
