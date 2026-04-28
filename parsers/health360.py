import pdfplumber
import re
from parsers.base import BaseParser
class Health360Parser(BaseParser):
    def __init__(self):
        self.name = "Health 360"
        self.raw_headers = ["Sr No", "Claim No", "Corporate", "CPR", "Member Name", "Treatment Date", "Diagnosis", "Invoice No", "Gross Amount", "Rejected", "Ded", "CoPay", "Net Paid", "Remarks"]
        self.formatted_headers = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"]

    def parse(self, file_path):
        rows = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                if not words: continue
                
                # To prevent missing rows at the top or bottom of the page due to missing border lines,
                # we explicitly add horizontal lines just above the highest text and just below the lowest text.
                min_top = min([w['top'] for w in words]) - 2
                max_bottom = max([w['bottom'] for w in words]) + 2
                
                table_settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "explicit_horizontal_lines": [min_top, max_bottom]
                }
                
                tables = page.extract_tables(table_settings)
                if not tables:
                    continue
                    
                for table in tables:
                    for r in table:
                        clean_row = []
                        for cell in r:
                            if cell is None:
                                clean_row.append("")
                            else:
                                # Replace newlines with spaces to keep data on one line per cell
                                clean_row.append(str(cell).replace("\n", " ").strip())
                                
                        # Filter out empty rows
                        if not any(clean_row):
                            continue
                            
                        # Filter out header/footer rows (the first column should contain a Sr No or be part of a valid record)
                        if not clean_row[0] or not clean_row[0].isdigit():
                            continue
                            
                        # Ensure we have the right number of columns (14 standard columns)
                        if len(clean_row) >= 14:
                            data = {
                                "Sr No": clean_row[0],
                                "Claim No": clean_row[1],
                                "Corporate": clean_row[2],
                                "CPR": clean_row[3],
                                "Member Name": clean_row[4],
                                "Treatment Date": clean_row[5],
                                "Diagnosis": clean_row[6],
                                "Invoice No": clean_row[7],
                                "Gross Amount": clean_row[8],
                                "Rejected": clean_row[9],
                                "Ded": clean_row[10],
                                "CoPay": clean_row[11],
                                "Net Paid": clean_row[12],
                                "Remarks": clean_row[13]
                            }
                            
                            row = [
                                data["Sr No"],
                                data["Claim No"],
                                data["Corporate"],
                                data["CPR"],
                                data["Member Name"],
                                data["Treatment Date"],
                                data["Diagnosis"],
                                data["Invoice No"],
                                data["Gross Amount"],
                                data["Rejected"],
                                data["Ded"],
                                data["CoPay"],
                                data["Net Paid"],
                                data["Remarks"]
                            ]
                            rows.append(row)
                        
        return rows

    def transform(self, raw_data):
        formatted_rows = []
        for r in raw_data:
            formatted_row = [
                r[0],   # Sl. No -> Sr No
                r[7],   # Inv No -> Invoice No
                r[5],   # Date -> Treatment Date
                r[3],   # Patient ID -> CPR
                r[4],   # Patient Name -> Member Name
                r[8],   # Invoice Balance -> Gross Amount
                r[12],  # Amt To Adjust -> Net Paid
                r[2],   # CustomerCode -> Corporate
                r[13],  # Remark 1 -> Remarks
                "",     # Remark 2
                ""      # Remark 3
            ]
            formatted_rows.append(formatted_row)
            
        return self.formatted_headers, formatted_rows
