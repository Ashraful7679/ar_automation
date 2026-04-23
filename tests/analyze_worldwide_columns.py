"""
Script to analyze Worldwide PDF structure focusing on finding specific columns
"""
import pdfplumber

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'

print("="*80)
print("ANALYZING WORLDWIDE PDF FOR NEW COLUMNS")
print("="*80)

target_keywords = ["PATIENT", "NAME", "DOB", "CLAIM", "ID", "DATE", "SERVICE", "CHARGE", "ALLOWED", "PATIENT", "RESP.", "CO-PAY", "COINSURANCE", "DEDUCTIBLE", "INELIGIBLE", "AMOUNTS", "REMARK", "CODES", "PAID", "PROVIDER", "INVOICE", "NUMBER"]

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"\n--- Page {page_num} ---")
        
        # 1. Check raw text for keywords
        text = page.extract_text()
        print("Text snippet (first 500 chars):")
        print(text[:500] if text else "No text found")
        
        # 2. Check Tables
        tables = page.extract_tables()
        if tables:
            print(f"\nFound {len(tables)} tables on this page.")
            for i, table in enumerate(tables):
                print(f"Table {i+1} (first 3 rows):")
                for row_idx, row in enumerate(table[:3]):
                    print(f"  Row {row_idx}: {row}")
        else:
            print("\nNo tables found on this page.")
