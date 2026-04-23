"""
Simple script to see the exact PDF table structure
"""
import pdfplumber

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    tables = page.extract_tables()
    
    if tables:
        table = tables[0]
        print("HEADER ROW:")
        print(table[0])
        print(f"\nNumber of columns: {len(table[0])}")
        
        print("\n" + "="*80)
        print("FIRST 5 DATA ROWS:")
        for i, row in enumerate(table[1:6], 1):
            print(f"\nRow {i}:")
            for j, cell in enumerate(row):
                print(f"  Column {j}: '{cell}'")
