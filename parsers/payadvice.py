import pdfplumber
import re
from parsers.base import BaseParser

class PayAdviceParser(BaseParser):
    def __init__(self):
        self.raw_headers = ["Invoice Number", "Invoice Date", "Invoice Details", "Invoice Amount"]
        self.formatted_headers = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"]

    def parse(self, file_path):
        """
        Parses PayAdvice PDF and extracts invoice data.
        Returns list of rows matching raw_headers.
        **BHD currency prefix is removed during extraction.**
        """
        rows = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract tables from the page
                tables = page.extract_tables()
                
                if tables:
                    table = tables[0]
                    
                    # Skip header row on first page only
                    start_idx = 1 if page_num == 1 else 0
                    
                    for row in table[start_idx:]:
                        # Skip empty rows
                        if not row or not any(row):
                            continue
                        
                        # Ensure row has at least 4 columns
                        while len(row) < 4:
                            row.append("")
                        
                        # Clean up row data and remove BHD from amount column
                        cleaned_row = []
                        for i, cell in enumerate(row[:4]):
                            cell_str = str(cell).strip() if cell else ""
                            
                            # Remove BHD from Invoice Amount column (index 3)
                            if i == 3:
                                cell_str = re.sub(r'^\s*BHD\s*', '', cell_str, flags=re.IGNORECASE).strip()
                            
                            cleaned_row.append(cell_str)
                        
                        # Only add if we have an invoice number
                        if cleaned_row[0]:
                            rows.append(cleaned_row)
        
        return rows

    def transform(self, raw_data):
        """
        Transforms raw PayAdvice data into standard output format.
        Note: BHD prefix is already removed in parse() method.
        
        Args:
            raw_data: List of lists matching raw_headers order
        
        Returns:
            (formatted_headers, formatted_rows)
        """
        formatted_rows = []
        
        for idx, row in enumerate(raw_data):
            # Extract fields from raw data
            invoice_number = row[1] if len(row) > 1 else ""  # Skip rowid at index 0
            invoice_date = row[2] if len(row) > 2 else ""
            invoice_details = row[3] if len(row) > 3 else ""
            invoice_amount = row[4] if len(row) > 4 else ""  # BHD already removed
            
            # BHD was already removed in parse(), but apply regex again as safety measure
            cleaned_amount = re.sub(r'^\s*BHD\s*', '', str(invoice_amount), flags=re.IGNORECASE).strip()
            cleaned_amount = cleaned_amount.replace(',', '')
            
            # Build formatted output row
            # Format: Sl. No, Inv No, Date, Patient ID, Patient Name, Invoice Balance, Amt To Adjust, CustomerCode, Remark
            formatted_row = [
                idx + 1,                    # Sl. No (auto-increment)
                invoice_number,             # Inv No
                invoice_date,               # Date
                "",                         # Patient ID (not available in PayAdvice)
                invoice_details,            # Patient Name (using Invoice Details)
                cleaned_amount,             # Invoice Balance (BHD removed)
                "",                         # Amt To Adjust (not available)
                "",                         # CustomerCode (not available)
                "",                         # Remark 1
                "",                         # Remark 2
                ""                          # Remark 3
            ]
            
            formatted_rows.append(formatted_row)
        
        return self.formatted_headers, formatted_rows
