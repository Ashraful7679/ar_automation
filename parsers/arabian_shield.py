import pdfplumber
import re
from parsers.base import BaseParser

class ArabianShieldParser(BaseParser):
    def __init__(self):
        self.raw_headers = ["Pass", "Insured No", "Insured Name", "HR/File No.", "Inv. No", "Inv. Date", "Claim.Tarif", "Deductible", "Requested", "VAT Amt", "Deduction", "VAT Deduction", "Payable", "VAT Net", "Tot Payable"]
        self.formatted_headers = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"]

    def parse(self, file_path):
        rows = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Visual Row Reconstruction
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                words.sort(key=lambda w: (w['top'], w['x0']))
                
                lines = []
                current_line = []
                last_top = 0
                
                for w in words:
                    if not current_line:
                        current_line.append(w)
                        last_top = w['top']
                    else:
                        if abs(w['top'] - last_top) < 5:
                            current_line.append(w)
                        else:
                            lines.append(current_line)
                            current_line = [w]
                            last_top = w['top']
                if current_line:
                    lines.append(current_line)
                    
                for line_words in lines:
                    line_words.sort(key=lambda w: w['x0'])
                    line_text = " ".join([w['text'] for w in line_words])
                    tokens = line_text.split()
                    
                    if not tokens: continue
                    if not re.match(r'^T\d+$', tokens[0]): continue
                    if len(tokens) < 15: continue
                    
                    # Date Anchor Logic
                    date_idx = -1
                    for idx, t in enumerate(tokens):
                        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', t):
                            date_idx = idx
                            break
                    
                    if date_idx == -1 or date_idx < 4: continue
                    
                    try:
                        pass_col = tokens[0]
                        insured_no = tokens[1]
                        hr_file = tokens[date_idx - 2]
                        inv_no = tokens[date_idx - 1]
                        inv_date = tokens[date_idx]
                        
                        name_tokens = tokens[2 : date_idx - 2]
                        insured_name = " ".join(name_tokens)
                        
                        numerics = tokens[date_idx+1 : date_idx+10]
                        if len(numerics) < 9:
                            numerics += [""] * (9 - len(numerics))
                            
                        # Store as dict for easier transformation, or list mapped to raw_headers
                        row = {
                            "Pass": pass_col,
                            "Insured No": insured_no,
                            "Insured Name": insured_name,
                            "HR/File No.": hr_file,
                            "Inv. No": inv_no,
                            "Inv. Date": inv_date,
                            "Tot Payable": numerics[8], # Last one is Tot Payable? Check logic_engine
                            # LogicEngine Order: Claim, Deductible, Requested, VAT Amt, Deduction, VAT Ded, Payable, VAT Net, Tot Payable
                            "Deductible": numerics[1],
                            # We only need specific cols for output, capturing all might be overkill but safe.
                        }
                        # Wait, logic_engine just stored them by index. 
                        # Let's stick to list to match logic_engine generic load
                        row_list = [
                            pass_col, insured_no, insured_name, hr_file, inv_no, inv_date, 
                            *numerics
                        ]
                        rows.append(row_list)
                    except Exception:
                        continue
        return rows

    def transform(self, raw_data):
        """
        raw_data: List of lists (matching self.raw_headers)
        Returns: (headers, formatted_rows)
        """
        formatted_rows = []
        for idx, row in enumerate(raw_data):
            # Map based on indices from raw_headers
            # 0: Pass, 1: Ins No, 2: Name, 3: HR, 4: Inv No, 5: Date, 6..14: Numerics
            
            # Target: Sl. No, Inv No, Date, Patient ID, Patient Name, Invoice Balance, Amt To Adjust, CustomerCode, Remark
            
            sl_no = idx + 1
            inv_no = row[4]
            inv_date = row[5]
            patient_id = row[1]
            patient_name = row[2]
            customer_code = row[3] # HR/File
            
            # Numerics start at index 6.
            # 6: Claim, 7: Deductible, 8: Requested, 9: VAT Amt, 10: Deduction, 11: VAT Ded, 12: Payable, 13: VAT Net, 14: Tot Payable
            
            # Invoice Balance -> Tot Payable -> Index 14
            invoice_balance = str(row[14]).replace(',', '')
            
            # Amt To Adjust -> Deductible -> Index 7
            amt_to_adjust = str(row[7]).replace(',', '')
            
            remark = ""
            
            formatted_rows.append([
                sl_no, inv_no, inv_date, patient_id, patient_name, invoice_balance, amt_to_adjust, customer_code, remark, "", ""
            ])
            
        return self.formatted_headers, formatted_rows
