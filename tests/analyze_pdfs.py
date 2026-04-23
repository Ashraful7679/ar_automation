import pdfplumber
import json

# Read PayAdvice PDF and extract all data
pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'

print("="*80)
print("PAYADVICE PDF ANALYSIS")
print("="*80)

with pdfplumber.open(pdf_path) as pdf:
    all_rows = []
    headers = None
    
    for page_num, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        
        if tables:
            table = tables[0]
            
            if not headers and table:
                headers = table[0]
                print(f"\nHeaders: {headers}\n")
            
            # Get data rows (skip header on first page)
            start_idx = 1 if page_num == 1 else 0
            for row in table[start_idx:]:
                if row and any(row):  # Skip empty rows
                    all_rows.append(row)
                    
    print(f"Total data rows: {len(all_rows)}\n")
    print("Sample rows:")
    for i, row in enumerate(all_rows[:10], 1):
        print(f"{i}. {row}")

print("\n" + "="*80)
print("WORLDWIDE INSURANCE PDF ANALYSIS")
print("="*80)

pdf_path2 = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'

try:
    with pdfplumber.open(pdf_path2) as pdf:
        all_rows2 = []
        headers2 = None
        
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            
            if tables:
                table = tables[0]
                
                if not headers2 and table:
                    headers2 = table[0]
                    print(f"\nHeaders: {headers2}\n")
                
                # Get data rows
                start_idx = 1 if page_num == 1 else 0
                for row in table[start_idx:]:
                    if row and any(row):
                        all_rows2.append(row)
                        
        print(f"Total data rows: {len(all_rows2)}\n")
        print("Sample rows:")
        for i, row in enumerate(all_rows2[:10], 1):
            print(f"{i}. {row}")
except Exception as e:
    print(f"Error: {e}")
