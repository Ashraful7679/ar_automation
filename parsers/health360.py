import pdfplumber
import re
from parsers.base import BaseParser

class Health360Parser(BaseParser):
    def __init__(self):
        self.raw_headers = ["Sr No", "Claim No", "Corporate", "CPR", "Member Name", "Treatment Date", "Diagnosis", "Invoice No", "Gross Amount", "Rejected", "Ded", "CoPay", "Net Paid", "Remarks"]
        self.formatted_headers = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"]

    def parse(self, file_path):
        rows = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        clean_row = []
                        for cell in row:
                            if cell is None:
                                clean_row.append("")
                            else:
                                clean_row.append(str(cell).replace("\n", " ").strip())
                        
                        # Filter out empty rows
                        if not any(clean_row):
                            continue
                            
                        # Filter out header rows (first column usually contains 'Sr No')
                        if "Sr" in clean_row[0] and "No" in clean_row[0]:
                            continue
                            
                        # Add valid data rows
                        if len(clean_row) == 14:
                            rows.append(clean_row)
        return rows

    def transform(self, raw_data):
        formatted_rows = []
        for idx, row in enumerate(raw_data):
            # Target Order: Sl. No, Inv No, Date, Patient ID, Patient Name, Invoice Balance, Amt To Adjust, CustomerCode, Remark 1, Remark 2, Remark 3
            # Mapping:
            # Sl No: idx+1
            # Inv No: row[7] (Invoice No)
            # Date: row[5] (Treatment Date)
            # Patient ID: row[3] (CPR)
            # Patient Name: row[4] (Member Name)
            # Invoice Balance: row[12] (Net Paid)
            # Amt To Adjust: row[10] (Ded)
            # CustomerCode: row[2] (Corporate)
            # Remark: row[13] (Remarks)
            
            sl_no = idx + 1
            inv_no = str(row[7]).strip()
            date = str(row[5]).strip()
            patient_id = str(row[3]).strip()
            patient_name = str(row[4]).strip()
            invoice_bal = str(row[12]).replace(',', '')
            amt_adj = str(row[10]).replace(',', '')
            cust_code = str(row[2]).strip()
            remark = str(row[13]).strip()
            
            formatted_rows.append([
                sl_no, inv_no, date, patient_id, patient_name, invoice_bal, amt_adj, cust_code, remark, "", ""
            ])
        return self.formatted_headers, formatted_rows
