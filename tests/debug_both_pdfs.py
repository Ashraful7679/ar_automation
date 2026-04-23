import pdfplumber
import json

# Read PayAdvice PDF
pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}\n")
    
    all_tables = []
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"PAGE {page_num}:")
        
        # Extract tables
        tables = page.extract_tables()
        print(f"Number of tables: {len(tables)}")
        
        if tables:
            for i, table in enumerate(tables):
                print(f"\n=== Table {i+1} ===")
                for j, row in enumerate(table):
                    print(f"Row {j}: {row}")
                all_tables.extend(table)
        print("\n" + "="*80 + "\n")

# Now do the same for Worldwide PDF
print("\n\n" + "="*100)
print("WORLDWIDE INSURANCE PAYMENT PDF")
print("="*100 + "\n")

pdf_path2 = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'

try:
    with pdfplumber.open(pdf_path2) as pdf:
        print(f"Total Pages: {len(pdf.pages)}\n")
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"PAGE {page_num}:")
            
            # Extract tables
            tables = page.extract_tables()
            print(f"Number of tables: {len(tables)}")
            
            if tables:
                for i, table in enumerate(tables):
                    print(f"\n=== Table {i+1} ===")
                    for j, row in enumerate(table):
                        print(f"Row {j}: {row}")
            print("\n" + "="*80 + "\n")
except Exception as e:
    print(f"Error reading Worldwide PDF: {e}")
