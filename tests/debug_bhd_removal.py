"""
Debug script to check actual data extraction and BHD removal
"""
import sys
sys.path.insert(0, r'D:\BrainyFlavors\File Conversion Soft\AR_Automation')

from parsers.payadvice import PayAdviceParser
import pdfplumber

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'

print("="*80)
print("DEBUGGING PAYADVICE PARSER - BHD REMOVAL")
print("="*80)

# Step 1: Check raw extraction
print("\n1. RAW PDF TABLE EXTRACTION:")
with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        if tables:
            table = tables[0]
            print(f"\nPage {page_num} - First 3 data rows:")
            for i, row in enumerate(table[:4], 1):
                print(f"  Row {i}: {row}")

# Step 2: Check parser.parse() output
print("\n" + "="*80)
print("2. PARSER.PARSE() OUTPUT:")
parser = PayAdviceParser()
raw_rows = parser.parse(pdf_path)
print(f"Total rows parsed: {len(raw_rows)}")
print("\nFirst 3 rows from parse():")
for i, row in enumerate(raw_rows[:3], 1):
    print(f"  {i}. {row}")
    print(f"     Invoice Amount column (index 3): '{row[3]}'")

# Step 3: Check transform with simulated rowid
print("\n" + "="*80)
print("3. PARSER.TRANSFORM() OUTPUT:")
simulated_data = [[i] + row for i, row in enumerate(raw_rows)]
print(f"\nFirst simulated row with rowid: {simulated_data[0]}")

headers, formatted_rows = parser.transform(simulated_data)
print(f"\nFormatted headers: {headers}")
print("\nFirst 3 formatted rows:")
for i, row in enumerate(formatted_rows[:3], 1):
    print(f"  {i}. {row}")
    print(f"     Invoice Balance (index 5): '{row[5]}'")

# Step 4: Test regex manually
print("\n" + "="*80)
print("4. MANUAL REGEX TEST:")
import re
test_amounts = ["BHD 33", "BHD 93.5", "BHD33", "  BHD  50.25", "BHD\t100"]
for amt in test_amounts:
    cleaned = re.sub(r'^\s*BHD\s*', '', amt, flags=re.IGNORECASE).strip()
    print(f"  '{amt}' -> '{cleaned}'")
