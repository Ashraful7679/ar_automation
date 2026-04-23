"""
Targeted search for specific table headers in Worldwide PDF
"""
import pdfplumber

pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'

target_headers = [
    "PATIENT", "NAME", "DOB", "CLAIM", "ID", "DATE", "OF", "SERVICE", 
    "CHARGE", "ALLOWED", "PATIENT", "RESP.", "CO-PAY", "COINSURANCE", 
    "DEDUCTIBLE", "INELIGIBLE", "AMOUNTS", "REMARK", "CODES", "PAID", 
    "PROVIDER", "INVOICE", "NUMBER"
]

print("SEARCHING FOR HEADERS...")

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"\n--- Page {page_num} ---")
        
        # 1. Search in text
        text = page.extract_text()
        if text:
            # Check if majority of keywords exist in text
            found_count = sum(1 for kw in target_headers if kw in text)
            print(f"Keywords found in text: {found_count}/{len(target_headers)}")
            if found_count > 5:
                print("Text snippet around keywords:")
                # Simple extraction of lines containing keywords
                lines = text.split('\n')
                for line in lines:
                    if any(kw in line for kw in ["PATIENT", "CLAIM", "INVOICE"]):
                        print(f"  {line}")
        
        # 2. Check Tables
        tables = page.extract_tables()
        if tables:
            print(f"Found {len(tables)} tables.")
            for i, table in enumerate(tables):
                # Check first few rows for header-like content
                # Flatten the first few rows to search for keywords
                header_candidates = []
                for row_idx in range(min(5, len(table))):
                    row_text = " ".join([str(cell or "") for cell in table[row_idx]])
                    header_candidates.append(row_text)
                    
                print(f"Table {i+1} candidate headers:")
                for hc in header_candidates:
                    match_count = sum(1 for kw in target_headers if kw in hc)
                    if match_count > 2:
                        print(f"  [MATCH {match_count}] {hc}")
                    else:
                        print(f"  [No match] {hc[:50]}...")
