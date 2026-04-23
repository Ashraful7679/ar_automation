import pdfplumber
import re
from parsers.base import BaseParser

class HealixParser(BaseParser):
    def __init__(self):
        self.raw_headers = [
            "Date", "Ref", "Description", "Debit", "Remitted"
        ]
        self.formatted_headers = [
            "Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", 
            "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"
        ]

    def parse(self, file_path):
        """
        Parses Healix International PDF.
        Example Row:
        85.13 12/05/2025 INV AOP032506928 Miss Alia Benzahra, Unknown 85.13 0.00 0.00
        
        Key Fields:
        - Date: 12/05/2025 (1st logical col)
        - Ref: AOP032506928 (2nd logical col - Inv No)
        - Description: Miss Alia Benzahra, Unknown (Name is before comma)
        - Debit: 85.13 (Balance)
        - Remitted: 0.00 (Amt to Adjust)
        """
        rows = []
        
        # Regex to capture: Date ... Type ... Ref ... Description ... Debit ... Credit ... Remitted
        # Note: Description can contain spaces. Amounts are at the end.
        # Strategy:
        # Anchor Date -> Type(INV) -> Ref(AOP...) -> Description(Non greedy) -> 3 or 4 floats at end
        
        pattern = re.compile(
            r'(?P<date>\d{2}/\d{2}/\d{4})\s+'       # 12/05/2025
            r'(?P<type>INV)\s+'                     # INV
            r'(?P<ref>AOP\d+)\s+'                   # AOP032506928
            r'(?P<desc>.+?)\s+'                     # Description (Name, etc)
            r'(?P<debit>[\d\.]+)\s+'                # Debit (85.13)
            r'(?P<credit>[\d\.]+)\s+'               # Credit (0.00)
            r'(?P<remitted>[\d\.]+)'                # Remitted (0.00)
            # Balance often follows but might be wrapped or handled by start of next line check
        )

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                for line in text.split('\n'):
                    match = pattern.search(line) # search finds it anywhere (handling leading 85.13)
                    if match:
                        d = match.groupdict()
                        rows.append((
                            d['date'],
                            d['ref'],
                            d['desc'].strip(),
                            d['debit'],
                            d['remitted'],
                        ))
        return rows

    def transform(self, raw_data):
        formatted_rows = []
        for idx, row in enumerate(raw_data):
            # row: Date, Ref, Desc, Debit, Remitted
            
            # Name Logic: "Miss Alia Benzahra, Unknown" -> "Miss Alia Benzahra"
            full_desc = row[2]
            if ',' in full_desc:
                patient_name = full_desc.split(',')[0].strip()
            else:
                patient_name = full_desc
            
            formatted_rows.append([
                idx + 1,            # Sl. No
                row[1],             # Inv No (Ref)
                row[0],             # Date
                "",                 # Patient ID
                patient_name,       # Patient Name
                str(row[3]).replace(',', ''),             # Invoice Balance (Debit)
                str(row[4]).replace(',', ''),             # Amt To Adjust (Remitted)
                "",                 # CustomerCode
                "",                 # Remark 1
                "",                 # Remark 2
                ""                  # Remark 3
            ])
        return self.formatted_headers, formatted_rows
