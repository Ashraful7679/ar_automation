"""
Check structure of Worldwide PDF tables
"""
import pdfplumber

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'

print("="*80)
print("CHECKING WORLDWIDE PDF TABLE STRUCTURE")
print("="*80)

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"\n--- Page {page_num} ---")
        tables = page.extract_tables()
        
        if tables:
            for i, table in enumerate(tables):
                print(f"\nTable {i+1}:")
                if table:
                    print(f"  Columns: {len(table[0])}")
                    print("  First 5 rows:")
                    for idx, row in enumerate(table[:5]):
                        # Sanitize row for printing
                        clean_row = [str(cell).replace('\n', ' ')[:20] + "..." if cell and len(str(cell)) > 20 else str(cell).replace('\n', ' ') if cell else "" for cell in row]
                        print(f"    Row {idx}: {clean_row}")
                else:
                    print("  Empty table")
        else:
            print("  No tables found")
