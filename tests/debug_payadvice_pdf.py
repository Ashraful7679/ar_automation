import pdfplumber

# Read PayAdvice PDF
pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}\n")
    
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"{'='*80}")
        print(f"PAGE {page_num}")
        print(f"{'='*80}\n")
        
        # Extract text
        text = page.extract_text()
        print("TEXT CONTENT:")
        print(text)
        print("\n")
        
        # Extract tables
        tables = page.extract_tables()
        print(f"Number of tables found: {len(tables)}\n")
        
        for i, table in enumerate(tables):
            print(f"--- Table {i+1} ---")
            for row in table:
                print(row)
            print("\n")
