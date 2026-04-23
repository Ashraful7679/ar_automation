"""
Dump table rows to find headers in Worldwide PDF
"""
import pdfplumber

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'

print("="*80)
print("DUMPING TABLE ROWS FROM WORLDWIDE PDF")
print("="*80)

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"\n--- Page {page_num} ---")
        tables = page.extract_tables()
        
        if tables:
            for i, table in enumerate(tables):
                print(f"\nTable {i+1} (First 5 rows):")
                for row_idx, row in enumerate(table[:5]):
                    # Clean None values for printing
                    clean_row = [str(cell).replace('\n', ' ') if cell else "None" for cell in row]
                    print(f"  Row {row_idx}: {clean_row}")
        else:
            print("No tables found.")
