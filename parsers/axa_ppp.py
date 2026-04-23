import pdfplumber
import re
from parsers.base import BaseParser

class AxaPppParser(BaseParser):
    def __init__(self):
        self.raw_headers = [
            "Patient Name", "Your Invoice Number", "Our Invoice ID", 
            "Amount Invoiced", "Amount Paid", "See Note", "Global Date"
        ]
        self.formatted_headers = [
            "Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", 
            "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"
        ]

    def parse(self, file_path):
        """
        Parses AXA PPP PDF using Regex.
        Row Format: Patient Name | Your Inv No | Our Inv ID | Cur Amt | Cur Amt | Note
        Extracts 'Date payment raised' from text for global date.
        """
        rows = []
        global_date = ""
        
        # Regex to capture fields. 
        pattern = re.compile(
            r'^(?P<patient>.+?)\s+'
            r'(?P<inv_no>[A-Z0-9-]+(?:-[A-Z]+)*)\s+'
            r'(?P<our_inv>\d+)\s+'
            r'(?P<amt_inv>[A-Z]{3}\s+[\d\.]+)\s+'
            r'(?P<amt_paid>[A-Z]{3}\s+[\d\.]+)'
            r'(?:\s+(?P<note>.*))?$'
        )

        with pdfplumber.open(file_path) as pdf:
            # First pass: Get Global Date
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # Look for "Date payment raised"
            # Format: Date payment raised\n04/06/2025
            date_match = re.search(r'Date payment raised\s*(\d{2}/\d{2}/\d{4})', full_text, re.IGNORECASE | re.MULTILINE)
            if not date_match:
                # Try finding just lines looking like dates near text? 
                # Or maybe it's "Date payment raised 04/06/2025"
                date_match = re.search(r'Date payment raised\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})', full_text, re.IGNORECASE)
            
            if date_match:
                global_date = date_match.group(1)

            # Second pass: Parse Lines
            lines = full_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                    
                match = pattern.match(line)
                if match:
                    data = match.groupdict()
                    
                    amt_inv = data['amt_inv'].split()[-1] if data['amt_inv'] else "0.00"
                    amt_paid = data['amt_paid'].split()[-1] if data['amt_paid'] else "0.00"
                    
                    # Logic: Split Inv No to extract Remark
                    # "OP05037625" -> Inv: OP05037625, Rem: ""
                    # "OP05037625-EX-GRATIA" -> Inv: OP05037625, Rem: EX-GRATIA
                    raw_inv = data['inv_no'].strip()
                    if '-' in raw_inv:
                        parts = raw_inv.split('-', 1)
                        inv_no = parts[0]
                        remark = parts[1]
                    else:
                        inv_no = raw_inv
                        remark = ""
                        
                    # Prepend existing note if any
                    note = data['note'].strip() if data['note'] else ""
                    if note:
                        remark = f"{remark} {note}".strip()

                    row = (
                        data['patient'].strip(),
                        inv_no,
                        data['our_inv'].strip(),
                        amt_inv,
                        amt_paid,
                        remark,
                        global_date
                    )
                    rows.append(row)
        return rows

    def transform(self, raw_data):
        """
        Maps raw data to Standard 9 Columns.
        Raw: Patient Name, Inv No, Our Inv ID, Amt Inv, Amt Paid, Remark, Global Date
        """
        formatted_rows = []
        for idx, row in enumerate(raw_data):
            # row index now has 7 elements
            patient_name = row[0]
            inv_no = row[1]
            our_inv_id = row[2]
            amt_inv = str(row[3]).replace(',', '')
            amt_paid = str(row[4]).replace(',', '')
            remark = row[5]
            global_date = row[6]

            sl_no = idx + 1
            date_val = "" # User Requested Blank
            patient_id = "" # User Requested Blank 
            
            # User Specs:
            # Inv No -> Your invoice number (processed)
            # Patient Name -> 1st Col
            # Invoice Balance -> Amount Invoiced
            # Amt To Adjust -> Amount Paid
            # CustomerCode -> Blank
            # Remark -> Suffix + Note
            
            new_row = [
                sl_no,
                inv_no,
                date_val,
                patient_id,
                patient_name,
                amt_inv,
                amt_paid,
                "",  # CustomerCode blank per request
                remark,                     # Remark 1
                "",                         # Remark 2
                ""                          # Remark 3
            ]
            formatted_rows.append(new_row)
            
        return self.formatted_headers, formatted_rows
