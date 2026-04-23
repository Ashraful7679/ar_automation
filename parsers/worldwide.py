import pdfplumber
import re
from parsers.base import BaseParser

class WorldwideParser(BaseParser):
    def __init__(self):
        # Specific headers provided by user
        self.raw_headers = [
            "PATIENT NAME", "DOB", "CLAIM ID", "DATE OF SERVICE", 
            "CHARGE", "ALLOWED", "PATIENT RESP.", "CO-PAY", 
            "COINSURANCE", "DEDUCTIBLE", "INELIGIBLE AMOUNTS", 
            "REMARK CODES", "PAID PROVIDER", "INVOICE NUMBER"
        ]
        self.formatted_headers = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"]

    def parse(self, file_path):
        """
        Parses Worldwide Insurance Payment PDF and extracts invoice data.
        Returns list of rows matching data structure.
        **BHD currency prefix is removed during extraction.**
        """
        rows = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract tables from the page
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        # Logic to identify if this is the correct table
                        # Check if it has enough columns (at least 14 based on user's list)
                        if not table:
                            continue
                            
                        # Find header row index
                        header_row_idx = -1
                        start_idx = 0
                        
                        # Inspect first few rows to find headers or data start
                        for r_idx, row in enumerate(table[:5]):
                            row_text = " ".join([str(c or "").upper() for c in row])
                            if "PATIENT NAME" in row_text or ("CLAIM" in row_text and "ID" in row_text):
                                header_row_idx = r_idx
                                start_idx = r_idx + 1
                                break
                        
                        # If no explicit header found, but column count matches 14, assume it's data
                        # (checking column count > 10 as heuristic)
                        effective_table = table[start_idx:]
                        
                        for row in effective_table:
                            # Skip empty rows
                            if not row or not any(row):
                                continue
                            
                            # Skip repeated header rows
                            row_text = " ".join([str(c or "").upper() for c in row])
                            if "PATIENT NAME" in row_text or "DATE OF SERVICE" in row_text:
                                continue

                            # Standardize row length to 14 columns
                            # If row is shorter, pad it; if longer, take first 14? 
                            # Usually better to ensure it has *structure* we expect.
                            # We'll pad to 14
                            current_row = row[:]
                            while len(current_row) < 14:
                                current_row.append("")
                            
                            # Extract relevant columns
                            # We need to clean the data
                            cleaned_row = []
                            for i, cell in enumerate(current_row[:14]):
                                cell_str = str(cell).strip() if cell else ""
                                
                                # Remove BHD from "PAID PROVIDER" column (index 12) or "CHARGE" (index 4)
                                # User previously asked to remove BHD from "Invoice Amount".
                                # In this format, "PAID PROVIDER" is likely the payment amount.
                                if i == 12:  # PAID PROVIDER column
                                    cell_str = re.sub(r'^\s*BHD\s*', '', cell_str, flags=re.IGNORECASE).strip()
                                
                                cleaned_row.append(cell_str)
                            
                            # Only add if we have an invoice number (index 13) or Patient Name (index 0)
                            # Checking Invoice Number (index 13) is robust
                            if cleaned_row[13] or cleaned_row[0]:
                                rows.append(cleaned_row)
        
        return rows

    def transform(self, raw_data):
        """
        Transforms raw Worldwide Insurance data into standard output format.
        Note: BHD prefix is already removed in parse() method.
        
        Args:
            raw_data: List of lists matching 14-column structure
        
        Returns:
            (formatted_headers, formatted_rows)
        """
        formatted_rows = []
        
        for idx, row in enumerate(raw_data):
            # Ensure row has enough columns
            if len(row) < 14:
                continue

            # Map Columns based on user provided list:
            # 0: PATIENT NAME -> Patient Name
            # 1: DOB
            # 2: CLAIM ID -> Patient ID
            # 3: DATE OF SERVICE -> Date
            # 4: CHARGE
            # 5: ALLOWED
            # 6: PATIENT RESP.
            # 7: CO-PAY
            # 8: COINSURANCE
            # 9: DEDUCTIBLE
            # 10: INELIGIBLE AMOUNTS -> Amt To Adjust (using this as placeholder)
            # 11: REMARK CODES -> Remark
            # 12: PAID PROVIDER -> Invoice Balance
            # 13: INVOICE NUMBER -> Inv No
            
            patient_name = row[0]
            patient_id = row[2]
            date_of_service = row[3]
            ineligible_amt = row[10]
            remark = row[11]
            paid_amount = row[12] # BHD removed in parse()
            invoice_number = row[13]
            
            # Additional cleaning if necessary (e.g., regex on BHD again for safety)
            cleaned_amount = re.sub(r'^\s*BHD\s*', '', str(paid_amount), flags=re.IGNORECASE).strip()
            cleaned_amount = cleaned_amount.replace(',', '')
            
            # Format: Sl. No, Inv No, Date, Patient ID, Patient Name, Invoice Balance, Amt To Adjust, CustomerCode, Remark
            formatted_row = [
                idx + 1,                    # Sl. No
                invoice_number,             # Inv No
                date_of_service,            # Date
                patient_id,                 # Patient ID
                patient_name,               # Patient Name
                cleaned_amount,             # Invoice Balance
                ineligible_amt,             # Amt To Adjust
                "",                         # CustomerCode
                remark,                     # Remark 1
                "",                         # Remark 2
                ""                          # Remark 3
            ]
            
            formatted_rows.append(formatted_row)
        
        return self.formatted_headers, formatted_rows
