"""
Prototype for updated Worldwide Parser logic
"""
import pdfplumber
import re

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'

target_headers = [
    "PATIENT NAME", "DOB", "CLAIM ID", "DATE OF SERVICE", 
    "CHARGE", "ALLOWED", "PATIENT RESP.", "CO-PAY", 
    "COINSURANCE", "DEDUCTIBLE", "INELIGIBLE AMOUNTS", 
    "REMARK CODES", "PAID PROVIDER", "INVOICE NUMBER"
]

print("PROTOTYPING NEW PARSER LOGIC...")

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"\n--- Page {page_num} ---")
        tables = page.extract_tables()
        
        if tables:
            for i, table in enumerate(tables):
                # 1. Check column count
                num_cols = len(table[0]) if table and table[0] else 0
                print(f"Table {i+1}: {num_cols} columns")
                
                # 2. Identify header row
                header_row_idx = -1
                for r_idx, row in enumerate(table[:10]): # Check first 10 rows
                    row_text = " ".join([str(cell or "").upper() for cell in row])
                    
                    # specific keywords to look for
                    if "PATIENT" in row_text and "NAME" in row_text and "CLAIM" in row_text:
                        header_row_idx = r_idx
                        print(f"  FOUND HEADER at row {r_idx}: {row}")
                        break
                
                if header_row_idx != -1:
                    print("  Extracting data...")
                    # Extract a few rows to verify
                    data_rows = table[header_row_idx+1:]
                    for j, d_row in enumerate(data_rows[:3]):
                        clean_row = [str(c).replace('\n', ' ') if c else "" for c in d_row]
                        print(f"    Data {j}: {clean_row}")
                        
                        # Check mappings
                        if len(d_row) >= 14:
                            print(f"      Pt Name: {d_row[0]}")
                            print(f"      Claim ID: {d_row[2]}")
                            print(f"      Service Date: {d_row[3]}")
                            print(f"      Paid Provider: {d_row[12]}")
                            print(f"      Invoice Num: {d_row[13]}")
