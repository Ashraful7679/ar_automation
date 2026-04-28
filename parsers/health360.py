import pdfplumber
import re
from parsers.base import BaseParser

class Health360Parser(BaseParser):
    def __init__(self):
        self.raw_headers = ["Sr No", "Claim No", "Corporate", "CPR", "Member Name", "Treatment Date", "Diagnosis", "Invoice No", "Gross Amount", "Rejected", "Ded", "CoPay", "Net Paid", "Remarks"]
        self.formatted_headers = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark"]

    def parse(self, file_path):
        rows = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                words.sort(key=lambda w: (w['top'], w['x0']))
                
                # Group words into physical lines
                lines = []
                if not words: continue
                
                current_line = [words[0]]
                last_top = words[0]['top']
                
                for w in words[1:]:
                    if abs(w['top'] - last_top) < 3:
                        current_line.append(w)
                    else:
                        lines.append(current_line)
                        current_line = [w]
                        last_top = w['top']
                lines.append(current_line)
                
                # Identify Row Blocks by Sr No (starts at x ~21 and is a number)
                row_blocks = []
                current_block = []
                
                for line in lines:
                    line.sort(key=lambda w: w['x0'])
                    first_word = line[0]
                    # Anchor: Sr No is a number at the start of the line (x < 30)
                    if first_word['x0'] < 30 and re.match(r'^\d+$', first_word['text']):
                        if current_block:
                            row_blocks.append(current_block)
                        current_block = [line]
                    elif current_block:
                        # Only add lines if we are already in a block and below header area
                        if first_word['top'] > 150:
                            current_block.append(line)
                
                if current_block:
                    row_blocks.append(current_block)
                
                for block in row_blocks:
                    # Process each block into columns
                    # Column zones based on analyzed X positions
                    # Sr No: 21, Claim No: 39, Corporate: 85, CPR: 141, Member Name: 194, 
                    # Date: 281, Diagnosis: 315, Inv No: 362, Gross: 409, Rej: 440, Ded: 477, CoPay: 499, Net: 531, Remarks: 562
                    
                    data = {h: [] for h in self.raw_headers}
                    
                    for line in block:
                        for w in line:
                            x = w['x0']
                            txt = w['text']
                            
                            if x < 35: data["Sr No"].append(txt)
                            elif x < 80: data["Claim No"].append(txt)
                            elif x < 135: data["Corporate"].append(txt)
                            elif x < 185: data["CPR"].append(txt)
                            elif x < 275: data["Member Name"].append(txt)
                            elif x < 310: data["Treatment Date"].append(txt)
                            elif x < 355: data["Diagnosis"].append(txt)
                            elif x < 405: data["Invoice No"].append(txt)
                            elif x < 435: data["Gross Amount"].append(txt)
                            elif x < 470: data["Rejected"].append(txt)
                            elif x < 495: data["Ded"].append(txt)
                            elif x < 525: data["CoPay"].append(txt)
                            elif x < 555: data["Net Paid"].append(txt)
                            else: data["Remarks"].append(txt)
                    
                    # Merge multi-line text
                    row = [
                        " ".join(data["Sr No"]),
                        " ".join(data["Claim No"]),
                        " ".join(data["Corporate"]),
                        " ".join(data["CPR"]),
                        " ".join(data["Member Name"]),
                        " ".join(data["Treatment Date"]),
                        " ".join(data["Diagnosis"]),
                        " ".join(data["Invoice No"]),
                        " ".join(data["Gross Amount"]),
                        " ".join(data["Rejected"]),
                        " ".join(data["Ded"]),
                        " ".join(data["CoPay"]),
                        " ".join(data["Net Paid"]),
                        " ".join(data["Remarks"])
                    ]
                    rows.append(row)
        return rows

    def transform(self, raw_data):
        formatted_rows = []
        for idx, row in enumerate(raw_data):
            # Target Order: Sl. No, Inv No, Date, Patient ID, Patient Name, Invoice Balance, Amt To Adjust, CustomerCode, Remark
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
                sl_no, inv_no, date, patient_id, patient_name, invoice_bal, amt_adj, cust_code, remark
            ])
        return self.formatted_headers, formatted_rows
