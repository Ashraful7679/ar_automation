import pdfplumber
import re
from parsers.base import BaseParser

class NextcareParser(BaseParser):
    def __init__(self):
        self.raw_headers = [
            "Invoice #", "Reference #", "Date", "Beneficiary Name", 
            "FOB", "Invoiced Amount", "Deducted Amount", "Settled Amount", "Remark"
        ]
        self.formatted_headers = [
            "Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", 
            "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"
        ]

    def parse(self, file_path):
        rows = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    for i, row in enumerate(table):
                        if not row or not row[0]:
                            continue
                        
                        cell = row[0].strip() if row[0] else ""
                        # Check if it's a remark row (starts with {{
                        if cell.startswith('{{'):
                            if rows:
                                rows[-1][-1] = cell
                            continue
                        
                        # Check if it's a data row - has invoice pattern at start
                        # Pattern: AIP/xxx, AOP/xxx, AOPxxx-, or C00xxx (reference number as invoice if no AOP/AIP)
                        if re.match(r'^(AIP\d+|AOP\d+|AOP\d+-[A-Z]|C\d+)', cell):
                            if len(row) >= 8 and row[5] and row[6] and row[7]:
                                try:
                                    # Clean invoice number: remove suffixes like /1, -A, /2, -B, /3, etc.
                                    inv = re.sub(r'[-/]\d+[A-Z]?$|[-/][A-Z]$', '', cell).strip()
                                    ref = row[1].strip() if row[1] else ""
                                    date = row[2].strip() if row[2] else ""
                                    name = row[3].strip() if row[3] else ""
                                    fob = row[4].strip() if row[4] else ""
                                    invoiced = row[5].replace(',', '') if row[5] else "0"
                                    deducted = row[6].replace(',', '') if row[6] else "0"
                                    settled = row[7].replace(',', '') if row[7] else "0"
                                    
                                    rows.append([
                                        inv, ref, date, name, fob,
                                        invoiced, deducted, settled, ""
                                    ])
                                except:
                                    pass
        
        return rows

    def transform(self, raw_data):
        formatted_rows = []
        for idx, row in enumerate(raw_data):
            # row: inv, ref, date, name, fob, invoiced, deducted, settled, remark
            if len(row) >= 9:
                inv, ref, date, name, fob, invoiced, deducted, settled, remark = row[:9]
            else:
                inv, ref, date, name, fob, invoiced, deducted, settled, remark = row[-9:]
            
            settled_amt = float(settled) if settled else 0
            invoiced_amt = float(invoiced) if invoiced else 0
            deducted_amt = float(deducted) if deducted else 0
            
            balance = invoiced_amt - settled_amt
            adjust = deducted_amt
            
            formatted_rows.append([
                idx + 1,
                inv,
                date,
                ref,
                name,
                str(balance),
                str(adjust),
                "",
                remark or "",
                "",
                ""
            ])
        return self.formatted_headers, formatted_rows