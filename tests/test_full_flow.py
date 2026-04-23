"""
Test the complete flow through LogicEngine to see where BHD appears
"""
import sys
sys.path.insert(0, r'D:\BrainyFlavors\File Conversion Soft\AR_Automation')

from logic_engine import LogicEngine

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'

print("="*80)
print("TESTING COMPLETE FLOW WITH LOGIC ENGINE")
print("="*80)

engine = LogicEngine(db_path=":memory:")

print("\n1. Loading file with PAY ADVICE profile...")
engine.load_file(pdf_path, profile_name='PAYADVICE')

print("\n2. Getting FORMATTED preview (this is what user sees in 'Converted Data'):")
preview = engine.get_formatted_preview()

print(f"\nHeaders: {preview['headers']}")
print(f"\nFirst 5 rows:")
for i, row in enumerate(preview['rows'][:5], 1):
    # Row structure: [rowid, Sl.No, Inv No, Date, Patient ID, Patient Name, Invoice Balance, ...]
    print(f"\nRow {i}:")
    print(f"  Sl. No: {row[1]}")
    print(f"  Inv No: {row[2]}")
    print(f"  Date: {row[3]}")
    print(f"  Patient Name: {row[5]}")
    print(f"  Invoice Balance: '{row[6]}'  <--- CHECK THIS FOR BHD")

print("\n" + "="*80)
print("3. Checking for BHD in Invoice Balance column:")
bhd_found = []
for i, row in enumerate(preview['rows'], 1):
    invoice_balance = str(row[6])
    if 'BHD' in invoice_balance.upper():
        bhd_found.append((i, invoice_balance))

if bhd_found:
    print(f"\n⚠️  BHD STILL PRESENT in {len(bhd_found)} rows:")
    for row_num, value in bhd_found[:5]:
        print(f"  Row {row_num}: '{value}'")
else:
    print("\n✅ NO BHD FOUND - Removal working correctly!")

engine.close()
