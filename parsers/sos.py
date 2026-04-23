import pdfplumber
import re
from parsers.base import BaseParser

class SosParser(BaseParser):
    def __init__(self):
        self.raw_headers = [
            "Document Reference Number", "Case Number", "Document Amount", "Global Total"
        ]
        self.formatted_headers = [
            "Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", 
            "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"
        ]

    def parse(self, file_path):
        """
        Parses International SOS PDF.
        Columns: Doc Ref, Case Num, Doc Amount, Bank, Swift.
        "Amt To Adjust" comes from the "Total" at the bottom of the file.
        """
        rows = []
        global_total = "0.00"
        
        # Regex for Data Rows: Ref (AOP...), Case (Alphanum), Amount (Number)
        # Assuming order: Ref ... Case ... Amount
        # Example: AOP042500550 ... JJNB010147 ... 29.80 BHD
        pattern = re.compile(
            r'(?P<ref>AOP\d+)\s+'                    # Doc Ref (AOP...)
            r'.*?'
            r'(?P<case>[A-Z0-9]+)\s+'               # Case Num
            r'.*?'
            r'(?P<amount>[\d,]+\.\d{2})'            # Doc Amount (29.80)
        )

        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # Extract Global Total from bottom area (look for "Total" followed by amount)
            # Example: Total 13,902.87 BHD
            # We look for the last occurrence or text explicitly labeled "Total"
            total_matches = re.findall(r'Total\s+.*?([\d,]+\.\d{2})', full_text, re.IGNORECASE)
            if total_matches:
                global_total = total_matches[-1] # Take the last one likely at bottom

            lines = full_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                
                match = pattern.search(line)
                if match:
                    d = match.groupdict()
                    rows.append((
                        d['ref'],
                        d['case'],
                        d['amount'],
                        global_total
                    ))
        return rows

    def transform(self, raw_data):
        """
        Maps raw data to Standard 9 Columns.
        Raw: Ref, Case, Amount, Global Total
        Target: Sl. No, Inv No, Date, Patient ID, Patient Name, Invoice Balance, Amt To Adjust, CustomerCode, Remark
        """
        formatted_rows = []
        for idx, row in enumerate(raw_data):
            # row: Ref, Case, Amount, Global Total
            
            ref = row[0]
            case = row[1]
            amount = row[2].replace(',', '') if row[2] else "0.00"
            total = row[3].replace(',', '') if row[3] else "0.00"

            formatted_rows.append([
                idx + 1,            # Sl. No
                ref,                # Inv No
                "",                 # Date (Blank)
                case,               # Patient ID
                "",                 # Patient Name (Blank)
                amount,             # Invoice Balance
                total,              # Amt To Adjust (Global Total)
                "",                 # CustomerCode (Blank)
                "",                 # Remark 1
                "",                 # Remark 2
                ""                  # Remark 3
            ])
        return self.formatted_headers, formatted_rows
