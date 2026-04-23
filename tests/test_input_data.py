"""
Test to verify BHD is removed from RAW parse output (Input Data table)
"""
import sys
sys.path.insert(0, r'D:\BrainyFlavors\File Conversion Soft\AR_Automation')

from parsers.payadvice import PayAdviceParser

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'

print("="*80)
print("TESTING BHD REMOVAL IN PARSE() METHOD (INPUT DATA)")
print("="*80)

parser = PayAdviceParser()

print("\n1. Calling parser.parse() - this populates the INPUT DATA table:")
raw_rows = parser.parse(pdf_path)

print(f"\nTotal rows: {len(raw_rows)}")
print(f"Raw headers: {parser.raw_headers}")

print("\n2. Checking first 5 rows for BHD:")
for i, row in enumerate(raw_rows[:5], 1):
    invoice_amount = row[3]  # Invoice Amount is column 3
    has_bhd = 'BHD' in str(invoice_amount).upper()
    status = "❌ BHD FOUND" if has_bhd else "✅ Clean"
    print(f"  Row {i}: Invoice={row[0]}, Amount='{invoice_amount}' {status}")

print("\n3. Checking ALL rows for BHD:")
bhd_count = 0
for row in raw_rows:
    if 'BHD' in str(row[3]).upper():
        bhd_count += 1

if bhd_count == 0:
    print(f"✅ SUCCESS! No BHD found in any of the {len(raw_rows)} rows")
    print("   BHD will NOT appear in Input Data table!")
else:
    print(f"⚠️  WARNING: BHD still present in {bhd_count} rows")
