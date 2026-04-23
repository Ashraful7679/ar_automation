import pdfplumber
import re
from parsers.base import BaseParser

class MshParser(BaseParser):
    def __init__(self):
        self.raw_headers = [
            "Invoice No", "Date", "Patient ID", "Patient Name", 
            "payment", "Deductible", "Message"
        ]
        self.formatted_headers = [
            "Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", 
            "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"
        ]

    def parse(self, file_path):
        """
        Parses MSH International PDF (Hierarchical Format).
        Structure:
        Header Row: Name (MSH ID) - Inv No (this is NOT the main invoice, just a reference)
        Detail Rows: Date - Remark ... Balance ... Adjust
        Message Section: Contains the actual Invoice No
        
        Example:
        AL MAJIDI WISAM (MSH 8155118) - US250317255  75,24 BHD ...
        20AUG2025 - Wisam Other specialist ... 20,00 BHD 18,00 BHD ...
        20AUG2025 - Wisam Medication ... 14,86 BHD ...
        Message:
        Invoice No: AOP082506242 ***
        """
        rows = []
        
        header_pattern = re.compile(r'^(?P<name>.+?)\s+\(MSH\s+(?P<id>\d+)\)\s+-\s+(?P<ref>[A-Z0-9]+)')
        
        detail_pattern = re.compile(
            r'^(?P<date>\d{2}[A-Z]{3}\d{4})\s+-\s+'
            r'(?P<remark>.+?)(\s+\d+(?:\s+\d{3})*,\d+\s*BHD)+$'
        )
        
        # Extract amounts like "1 367,88 BHD" - the first number is part of the amount (European thousands)
        amounts_pattern = re.compile(r'(\d+(?:\s+\d{3})*,\d+)\s*BHD')
        
        message_pattern = re.compile(r'Invoice No:\s*([A-Z0-9]+)\s*\*\*\*\s*(.+)$')

        current_header = None
        pending_rows = []
        pending_message = ""
        pending_invoice = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    # Check for header line first
                    h_match = header_pattern.match(line)
                    if h_match:
                        # Flush any pending rows with old message before starting new section
                        if pending_rows:
                            if pending_message and pending_invoice:
                                for row in pending_rows:
                                    row[0] = pending_invoice
                                    row[-1] = pending_message
                            else:
                                # No message came - use header reference as invoice
                                for row in pending_rows:
                                    row[0] = current_header.get('ref', row[0])
                            rows.extend(pending_rows)
                        pending_rows = []
                        pending_message = ""
                        pending_invoice = ""
                        current_header = h_match.groupdict()
                        continue
                    
                    # Check for message with invoice (after ***)
                    msg_match = message_pattern.search(line)
                    if msg_match and current_header:
                        pending_invoice = msg_match.group(1)
                        pending_message = msg_match.group(2).strip()
                        
                        # Check if there are more lines in the message
                        continue
                    
                    # Collect more lines for message until we hit another relevant line
                    if pending_message and pending_invoice and current_header:
                        # If we hit another invoice message, flush old message first
                        if line.startswith('Invoice No:'):
                            # Apply current message to pending rows
                            if pending_rows:
                                for row in pending_rows:
                                    row[0] = pending_invoice
                                    row[-1] = pending_message
                                rows.extend(pending_rows)
                            # Start new message
                            pending_rows = []
                            msg_match_new = re.search(line)
                            if msg_match_new:
                                pending_invoice = msg_match_new.group(1)
                                pending_message = msg_match_new.group(2).strip()
                            continue
                        # If we hit a new header, flush and continue
                        elif header_pattern.match(line):
                            if pending_rows:
                                for row in pending_rows:
                                    row[0] = pending_invoice
                                    row[-1] = pending_message
                                rows.extend(pending_rows)
                            pending_rows = []
                            pending_message = ""
                            pending_invoice = ""
                            current_header = header_pattern.match(line).groupdict()
                            continue
                        # Add non-header lines to message
                        elif not line.startswith('AL ') and not line.startswith('***'):
                            pending_message += " " + line.strip()
                    
                    # Handle detail rows - only when there's no pending message
                    if current_header and not pending_message:
                        d_match = detail_pattern.match(line)
                        if d_match:
                            data = d_match.groupdict()
                            date = data['date']
                            remark = data['remark'].strip()
                            
                            # Extract amounts like "1 367,88 BHD"
                            amounts_list = amounts_pattern.findall(line)
                            
                            if amounts_list and len(amounts_list) >= 3:
                                # amounts_list = ['1 367,88', '1 367,88', '1 367,88']
                                # First amount = Original Charge (Invoice Balance)
                                # Second amount = Payment (what was actually paid)
                                # Third amount = Deductible (Amt To Adjust)
                                def parse_amount(amt_str):
                                    # Remove space between digits (European thousands): "1 367,88" -> "1367,88"
                                    cleaned = amt_str.replace(' ', '')
                                    return cleaned.replace(',', '.')
                                
                                orig_charge = parse_amount(amounts_list[0])
                                payment = parse_amount(amounts_list[1])
                                deductible = parse_amount(amounts_list[2])
                                
                                bal = orig_charge
                                adj = deductible
                            elif amounts_list and len(amounts_list) == 2:
                                # Only 2 amounts - use first as balance, second as adjust
                                bal = amounts_list[0][1].replace('BHD', '').replace(',', '.')
                                adj = amounts_list[1][1].replace('BHD', '').replace(',', '.')
                            else:
                                bal = "0.00"
                                adj = "0.00"

                            pending_rows.append([
                                current_header['ref'],
                                date,
                                current_header['id'],
                                current_header['name'],
                                bal,
                                adj,
                                remark
                            ])
                
                if pending_rows and current_header:
                    if pending_message and pending_invoice:
                        for row in pending_rows:
                            row[0] = pending_invoice
                            row[-1] = pending_message
                    else:
                        for row in pending_rows:
                            row[0] = current_header.get('ref', row[0])
                    rows.extend(pending_rows)
                    pending_rows = []
                            
        return rows

    def transform(self, raw_data):
        formatted_rows = []
        for idx, row in enumerate(raw_data):
            # row: Inv, Date, ID, Name, Bal, Adj, Remark
            formatted_rows.append([
                idx + 1,            # Sl. No
                row[0],             # Inv No
                row[1],             # Date
                row[2],             # Patient ID
                row[3],             # Patient Name
                str(row[4]).replace(',', ''),             # Invoice Balance
                str(row[5]).replace(',', ''),             # Amt To Adjust
                "",                 # CustomerCode
                row[6],             # Remark 1
                "",                 # Remark 2
                ""                  # Remark 3
            ])
        return self.formatted_headers, formatted_rows
