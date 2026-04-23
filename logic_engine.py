import psycopg2
from psycopg2 import pool
import csv
import openpyxl
import os
import xlrd
from pypdf import PdfReader
import re
import pandas as pd
from parsers.arabian_shield import ArabianShieldParser
from parsers.axa_ppp import AxaPppParser
from parsers.msh import MshParser
from parsers.healix import HealixParser
from parsers.sos import SosParser
from parsers.gems import GemsParser
from parsers.payadvice import PayAdviceParser
from parsers.worldwide import WorldwideParser
from parsers.nextcare import NextcareParser
from fpdf import FPDF
from datetime import datetime
import sys

class LogicEngine:
    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self.conn = psycopg2.connect(db_path, connect_timeout=30)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()
        self.table_name = "raw_data"
        self.formatted_table_name = "formatted_data"
        self.headers = []
        self.formatted_headers = []
        self.current_parser = None
        
        self._recover_raw_headers()
        self._recover_formatted_headers()

    def _get_base_path(self):
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.dirname(os.path.abspath(__file__))
        
    def _recover_formatted_headers(self):
        """Recovers headers from the existing formatted_data table schema"""
        try:
            self.cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{self.formatted_table_name}'")
            cols = self.cursor.fetchall()
            if cols:
                self.formatted_headers = [c[0] for c in cols]
        except Exception:
            pass

    def _recover_raw_headers(self):
        """Recovers headers from the existing raw_data table schema"""
        try:
            self.cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{self.table_name}'")
            cols = self.cursor.fetchall()
            if cols:
                self.headers = [c[0] for c in cols]
        except Exception:
            pass

    def _get_parser(self, profile_name):
        if profile_name == 'ARABIAN_SHIELD':
            return ArabianShieldParser()
        elif profile_name == 'AXA_PPP':
            return AxaPppParser()
        elif profile_name == 'MSH':
            return MshParser()
        elif profile_name == 'HEALIX':
            return HealixParser()
        elif profile_name == 'SOS':
            return SosParser()
        elif profile_name == 'GEMS':
            return GemsParser()
        elif profile_name == 'PAYADVICE':
            return PayAdviceParser()
        elif profile_name == 'WORLDWIDE':
            return WorldwideParser()
        elif profile_name == 'NEXT_CARE':
            return NextcareParser()
        return None

    def _run_parser(self, parser_instance, file_path):
        """Helper to run a specific parser"""
        self.current_parser = parser_instance
        try:
            rows = self.current_parser.parse(file_path)
        except Exception as e:
            print(f"Parser Error: {e}")
            raise e
        
        self.headers = self.current_parser.raw_headers
        self._create_table(self.headers)
        if rows:
            placeholder = ','.join(['%s']*len(self.headers))
            cols = ', '.join([f'"{h}"' for h in self.headers])
            self.cursor.executemany(f"INSERT INTO {self.table_name} ({cols}) VALUES ({placeholder})", rows)
        self.conn.commit()
    
    def _create_formatted_table(self, headers):
        cols = [f'"{h}" TEXT' for h in headers]
        cols.insert(0, 'id SERIAL PRIMARY KEY')
        self.cursor.execute(f"DROP TABLE IF EXISTS {self.formatted_table_name}")
        self.cursor.execute(f"CREATE TABLE {self.formatted_table_name} ({', '.join(cols)})")

    def _persist_formatted_data(self):
        if not self.current_parser:
             return
        
        self.cursor.execute(f'SELECT * FROM {self.table_name}')
        col_names = [desc[0] for desc in self.cursor.description]
        if 'id' in col_names:
            col_names.remove('id')
        
        self.cursor.execute(f"SELECT {', '.join(col_names)} FROM {self.table_name}")
        raw_rows = self.cursor.fetchall()
        
        self.formatted_headers, formatted_rows = self.current_parser.transform(raw_rows)
        
        self._create_formatted_table(self.formatted_headers)
        
        if formatted_rows:
            placeholder = ','.join(['%s']*len(self.formatted_headers))
            self.cursor.executemany(f"INSERT INTO {self.formatted_table_name} ({', '.join([f'\"{h}\"' for h in self.formatted_headers])}) VALUES ({placeholder})", formatted_rows)
        self.conn.commit()

    def load_file(self, file_path, profile_name='default', sheet_name=None):
        """Loads Excel, CSV, or PDF into SQLite table"""
        ext = os.path.splitext(file_path)[1].lower()
        
        self.cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
        
        # Select Parser for PDF
        if ext == '.pdf':
            self.current_parser = self._get_parser(profile_name)
            if self.current_parser:
                self._run_parser(self.current_parser, file_path)
                self._persist_formatted_data() # SAVE CONVERTED STATE
            else:
                self._load_pdf(file_path) # Fallback to generic
            return

        elif ext == '.csv':
            self._load_csv(file_path)
        elif ext in ['.xlsx', '.xlsm']:
            self._load_excel(file_path, sheet_name)
        elif ext == '.xls':
            self._load_xls(file_path, sheet_name)
        elif ext == '.pdf': # Generic PDF Fallback logic if needed but handled above
            self._load_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def get_formatted_preview(self):
        """Returns the transformed data for preview"""
        if self.current_parser:
            placeholders = ', '.join([f'"{h}"' for h in self.formatted_headers])
            self.cursor.execute(f"SELECT id, {placeholders} FROM {self.formatted_table_name}")
            rows = self.cursor.fetchall()
            
            return {
                "headers": ["_id"] + self.formatted_headers, 
                "rows": rows
            }
        else:
            return self.get_preview()

    FIXED_HEADERS = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"]

    def generate_custom_output(self, profile_name=None, custom_filename=None, file_format='xlsx'):
        """Generates a formatted Excel, CSV, or PDF file"""
        # Determine Output Directory
        if getattr(sys, 'frozen', False):
             # Frozen: Write to 'output' folder next to EXE
             base_dir = os.path.dirname(sys.executable)
             output_dir = os.path.join(base_dir, 'output')
        else:
             # Dev: Write to static/output
             output_dir = os.path.join(self._get_base_path(), 'static', 'output')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine Base Filename
        if custom_filename:
             base_name = os.path.splitext(custom_filename)[0]
        else:
             base_name = f"Formatted_Output_{profile_name}" if profile_name else "Processed_Output"
             
        # Determine Extension
        ext = file_format.lower()
        if ext not in ['xlsx', 'csv', 'pdf', 'xls', 'xlsm']:
            ext = 'xlsx'
        filename = base_name + f".{ext}"
        output_path = os.path.join(output_dir, filename)
        
        # Get all data for export
        if not self.formatted_headers:
             self._recover_formatted_headers()

        # Force Fixed Headers if missing
        if not self.formatted_headers:
             self.formatted_headers = self.FIXED_HEADERS

        # Strict Formatted Data Query
        query_cols = ', '.join([f'"{h}"' for h in self.formatted_headers])
        
        try:
             # Check if table exists
             self.cursor.execute(f"SELECT 1 FROM {self.formatted_table_name} LIMIT 1")
             # It exists. Select Data.
             self.cursor.execute(f"SELECT {query_cols} FROM {self.formatted_table_name}")
             formatted_rows = list(self.cursor.fetchall())
             formatted_headers = list(self.formatted_headers)
        except Exception as e:
             # Table missing or query failed. Return EMPTY Fixed Shell.
             formatted_headers = list(self.formatted_headers)
             formatted_rows = []
        
        # Combine Remark columns if we have 3 (Remark 1, 2, 3)
        if len(formatted_headers) >= 11:
            r1_idx = formatted_headers.index("Remark 1") if "Remark 1" in formatted_headers else -1
            r2_idx = formatted_headers.index("Remark 2") if "Remark 2" in formatted_headers else -1
            r3_idx = formatted_headers.index("Remark 3") if "Remark 3" in formatted_headers else -1
            
            if r1_idx >= 0:
                combined_remarks = []
                for row in formatted_rows:
                    remarks = []
                    if r1_idx < len(row) and row[r1_idx]: remarks.append(row[r1_idx])
                    if r2_idx < len(row) and row[r2_idx]: remarks.append(row[r2_idx])
                    if r3_idx < len(row) and row[r3_idx]: remarks.append(row[r3_idx])
                    combined = ", ".join([r for r in remarks if r])
                    # Create new row with single Remarks column
                    new_row = list(row[:r1_idx]) + [combined] + list(row[r1_idx+3:])
                    combined_remarks.append(new_row)
                formatted_rows = combined_remarks
                # Update headers to single Remarks
                new_headers = list(formatted_headers[:r1_idx]) + ["Remarks"] + list(formatted_headers[r1_idx+3:])
                formatted_headers = new_headers

        # Export Logic
        if ext == 'csv':
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # Custom Requirement: 4 Blank Rows for CSV too
                for _ in range(4):
                    writer.writerow([])
                writer.writerow(formatted_headers)
                writer.writerows(formatted_rows)
        elif ext == 'pdf':
            self._generate_pdf(output_path, formatted_headers, formatted_rows, profile_name)
        elif ext == 'xls':
            try:
                # Use Pandas for Legacy XLS
                df = pd.DataFrame(formatted_rows, columns=formatted_headers)
                df.to_excel(output_path, index=False, startrow=4)
            except Exception as e:
                print(f"Failed to export XLS (xlwt missing?): {e}")
                # Fallback: Write CSV content to the .xls file
                # This creates a file that Excel will open (with a warning)
                with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    for _ in range(4): writer.writerow([])
                    writer.writerow(formatted_headers)
                    writer.writerows(formatted_rows)
        elif ext in ['xlsx', 'xlsm']:
            # XLSX and XLSM (OpenPyXL)
            from openpyxl.styles import numbers
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Data"
            
            # Custom Requirement: 4 Blank Rows at start
            for _ in range(4):
                ws.append([])
            
            ws.append(formatted_headers)
            for r in formatted_rows:
                ws.append(r)
            
            # Convert Balance and Adjust columns to numbers (columns F=6, G=7 in 1-indexed)
            for row in ws.iter_rows(min_row=5, max_row=ws.max_row, min_col=6, max_col=7):
                for cell in row:
                    if cell.value:
                        try:
                            cell.value = float(str(cell.value).replace(',', ''))
                            cell.number_format = numbers.FORMAT_NUMBER_00
                        except:
                            pass
            
            wb.save(output_path)
        
        return filename

    def _generate_pdf(self, output_path, headers, rows, profile_name):
        """Generates a professional branded PDF"""
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # --- Header Section ---
        logo_path = os.path.join(self._get_base_path(), 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            pdf.image(logo_path, 10, 8, 33)
        
        pdf.set_font('helvetica', 'B', 20)
        pdf.set_text_color(31, 41, 55) # Deep Gray
        pdf.cell(80) # Move to the right
        pdf.cell(100, 10, 'AR Report', 0, 1, 'L')
        
        pdf.set_font('helvetica', '', 10)
        pdf.set_text_color(107, 114, 128) # Gray
        pdf.cell(80)
        pdf.cell(100, 5, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'L')
        pdf.cell(80)
        pdf.cell(100, 5, f'Payer Profile: {profile_name or "General"}', 0, 1, 'L')
        pdf.ln(20) # Spacer
        
        # --- Table Section ---
        pdf.set_font('helvetica', 'B', 9)
        pdf.set_fill_color(243, 244, 246) # Light Gray highlight
        pdf.set_text_color(0, 0, 0)
        
        # Header widths (approximate for A4 Landscape - 297mm - 20mm margins = 277mm)
        # 0:Sl, 1:Inv, 2:Date, 3:PID, 4:PName, 5:Balance, 6:Amount, 7:CustCode, 8:Status
        widths = [12, 35, 25, 30, 60, 25, 25, 35, 30] 
        
        # Render Headers
        for i, h in enumerate(headers):
            pdf.cell(widths[i], 10, str(h), 1, 0, 'C', 1)
        pdf.ln()
        
        # Render Rows
        pdf.set_font('helvetica', '', 8)
        total_bal = 0
        total_adj = 0
        
        for r in rows:
            # Check for page break
            if pdf.get_y() > 175:
                pdf.add_page()
                pdf.set_font('helvetica', 'B', 9)
                pdf.set_fill_color(243, 244, 246)
                for i, h in enumerate(headers):
                    pdf.cell(widths[i], 10, str(h), 1, 0, 'C', 1)
                pdf.ln()
                pdf.set_font('helvetica', '', 8)

            for i, cell in enumerate(r):
                val = str(cell) if cell is not None else ""
                align = 'L'
                if i in [0, 5, 6]: align = 'R'
                
                # Truncate if too long
                max_w = widths[i] - 2
                if pdf.get_string_width(val) > max_w:
                    while pdf.get_string_width(val + "...") > max_w and len(val) > 0:
                        val = val[:-1]
                    val = val + "..."
                
                pdf.cell(widths[i], 8, val, 1, 0, align)
            
            try:
                bal_str = str(r[5]).replace(',', '') if r[5] else '0'
                adj_str = str(r[6]).replace(',', '') if r[6] else '0'
                total_bal += float(bal_str) if bal_str else 0
                total_adj += float(adj_str) if adj_str else 0
            except: pass
            
            pdf.ln()
            
        # --- Totals Row ---
        pdf.set_font('helvetica', 'B', 9)
        pdf.set_fill_color(249, 250, 251)
        pdf.cell(widths[0], 10, "", 1, 0, 'C', 1)
        pdf.cell(widths[1] + widths[2] + widths[3] + widths[4], 10, "GRAND TOTALS", 1, 0, 'R', 1)
        pdf.cell(widths[5], 10, f"{total_bal:,.2f}", 1, 0, 'R', 1)
        pdf.cell(widths[6], 10, f"{total_adj:,.2f}", 1, 0, 'R', 1)
        pdf.cell(widths[7] + widths[8], 10, "", 1, 0, 'C', 1)
        pdf.ln(15)
        
        pdf.set_font('helvetica', 'I', 8)
        pdf.set_text_color(156, 163, 175)
        pdf.cell(0, 10, "Note: This is a system-generated report. Confidential.", 0, 1, 'C')
        pdf.cell(0, 5, f"Verified by: ____________________   Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1, 'R')
        
        pdf.output(output_path)

    def update_formatted_cell(self, row_id, col_index, new_value):
        """Updates a cell in the formatted_data table."""
        if not self.formatted_headers:
             self._recover_formatted_headers()
        
        if not self.formatted_headers:
             return False

        if col_index < 0 or col_index >= len(self.formatted_headers):
            raise ValueError("Invalid column index")
            
        col_name = self.formatted_headers[col_index]
        self.cursor.execute(f'UPDATE {self.formatted_table_name} SET "{col_name}" = %s WHERE id = %s', (new_value, row_id))
        self.conn.commit()
        return True

    def update_formatted_cells_batch(self, updates):
        """Batch update cells. updates = list of {row_id, col_index, value}"""
        if not self.formatted_headers:
             self._recover_formatted_headers()
        
        if not self.formatted_headers:
             return False
        
        updates_by_col = {}
        for u in updates:
            idx = int(u['col_index'])
            if idx < 0 or idx >= len(self.formatted_headers): continue
            col_name = self.formatted_headers[idx]
            
            if col_name not in updates_by_col:
                updates_by_col[col_name] = []
            
            updates_by_col[col_name].append((u['value'], u['row_id']))
            
        for col_name, batch in updates_by_col.items():
            self.cursor.executemany(f'UPDATE {self.formatted_table_name} SET "{col_name}" = %s WHERE id = %s', batch)
            
        self.conn.commit()
        return True

    def overwrite_formatted_data(self, rows):
        """Overwrites the formatted_data table with new rows."""
        if not self.formatted_headers:
             self._recover_formatted_headers()
        
        if not self.formatted_headers:
             self.formatted_headers = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"]
             
        self._create_formatted_table(self.formatted_headers)
        if rows:
            placeholder = ','.join(['%s']*len(self.formatted_headers))
            cols = ', '.join([f'"{h}"' for h in self.formatted_headers])
            self.cursor.executemany(f"INSERT INTO {self.formatted_table_name} ({cols}) VALUES ({placeholder})", rows)
        self.conn.commit()

    def _load_csv(self, path):
        df = pd.read_csv(path)
        self._process_dataframe(df)

    def _load_excel(self, path, sheet_name=None):
        # Check if it's SpreadsheetML XML (BUPA)
        with open(path, 'rb') as f:
            header_check = f.read(512).decode('utf-8', errors='ignore')
        
        if '<?xml' in header_check[:200] and 'spreadsheet' in header_check.lower():
            df = self._parse_spreadsheetml(path)
        else:
            try:
                # Normal Excel
                if sheet_name:
                    df = pd.read_excel(path, sheet_name=sheet_name)
                else:
                    df = pd.read_excel(path)
            except Exception as e:
                # Fallback to HTML/XML if it's actually an HTML table renamed to .xls
                try:
                    dfs = pd.read_html(path, flavor='html.parser')
                    df = dfs[0] if dfs else pd.DataFrame()
                except:
                    raise e
                    
        self._process_dataframe(df)

    def _parse_spreadsheetml(self, path):
        """Native parser for Microsoft SpreadsheetML XML files (BUPA/Allianz format)."""
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except Exception as e:
            print(f"ET.parse failed: {e}")
            return pd.DataFrame()
        
        # Namespaces
        ns = {
            'ss': 'urn:schemas-microsoft-com:office:spreadsheet',
            'x': 'urn:schemas-microsoft-com:office:spreadsheet'
        }
        
        # Get first worksheet
        worksheet = root.find('.//ss:Worksheet', ns)
        if worksheet is None:
            worksheet = root.find('.//x:Worksheet', ns)
        
        if worksheet is None:
            return pd.DataFrame()
            
        data = []
        table = worksheet.find('.//ss:Table', ns) or worksheet.find('.//x:Table', ns)
        if table is not None:
            for row_elem in table.findall('.//ss:Row', ns) or table.findall('.//x:Row', ns):
                row_data = {}
                col_idx = 0
                for cell_elem in row_elem.findall('.//ss:Cell', ns) or row_elem.findall('.//x:Cell', ns):
                    # Handle ss:Index (skipped columns)
                    index = cell_elem.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                    if index:
                        col_idx = int(index) - 1
                    
                    data_elem = cell_elem.find('.//ss:Data', ns) or cell_elem.find('.//x:Data', ns)
                    if data_elem is not None:
                        row_data[col_idx] = data_elem.text
                    col_idx += 1
                data.append(row_data)
        
        df = pd.DataFrame(data)
        if not df.empty:
            # Fill missing columns with None and sort by index
            cols = sorted(df.columns)
            df = df.reindex(columns=cols)
        
        return df

    def _process_dataframe(self, df):
        """Common logic to clean and save a dataframe to the DB"""
        df = self._detect_and_fix_headers(df)
        
        # Convert all columns to string to avoid formatting issues
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].astype(str).replace('NaT', None)

        self.headers = [str(c).strip() for c in df.columns]
        self.headers = [h if h and h != 'nan' else f"col_{i}" for i, h in enumerate(self.headers)]
        self.headers = self._deduplicate_headers(self.headers)
        
        self._create_table(self.headers)
        
        # Clean numeric columns - remove commas from values that look like money
        rows = df.astype(object).where(pd.notnull(df), None).values.tolist()
        rows = self._clean_numeric_columns(rows)
        
        if rows:
            placeholder = ','.join(['%s']*len(self.headers))
            cols = ', '.join([f'"{h}"' for h in self.headers])
            self.cursor.executemany(f"INSERT INTO {self.table_name} ({cols}) VALUES ({placeholder})", rows)
        self.conn.commit()

    def _clean_numeric_columns(self, rows):
        """Remove commas from numeric-looking values"""
        cleaned_rows = []
        for row in rows:
            cleaned_row = []
            for val in row:
                if val is None:
                    cleaned_row.append(None)
                elif isinstance(val, str):
                    # Check if it looks like a number with comma (e.g., "2,145.240" or "1,000")
                    if re.match(r'^\d{1,3}(,\d{3})*(\.\d+)?$', val.strip()):
                        cleaned_row.append(val.replace(',', ''))
                    else:
                        cleaned_row.append(val)
                else:
                    cleaned_row.append(val)
            cleaned_rows.append(cleaned_row)
        return cleaned_rows

    def _detect_and_fix_headers(self, df):
        """Attempts to find the actual header row by scanning first 10 rows."""
        keywords = ['invoice', 'date', 'patient', 'name', 'amount', 'balance', 'code', 'member', 'policy', 'rec', 'no']
        best_idx = -1
        max_matches = 0
        
        # Check current columns (Level 0)
        current_cols = [str(c).lower() for c in df.columns]
        current_matches = sum(1 for k in keywords if any(k in c for c in current_cols))
        max_matches = current_matches

        # Check first 10 rows
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            row_str = [str(cell).lower() for cell in row if pd.notnull(cell)]
            matches = sum(1 for k in keywords if any(k in r for r in row_str))
            
            if matches > max_matches:
                max_matches = matches
                best_idx = i
        
        # Special handling for HEALTH 360 files with "Out-patient" in column
        if best_idx == -1 and len(df) > 1:
            row1_str = [str(df.iloc[1, c]).lower() for c in range(min(5, len(df.columns)))]
            if any('invoice' in c or 'batch' in c or 'claim' in c for c in row1_str):
                best_idx = 1
        
        # Only promote if found better row AND columns are not generic
        if best_idx != -1 and max_matches > 0 and not any('Col' in str(c) for c in df.columns):
            df.columns = df.iloc[best_idx]
            df = df.iloc[best_idx + 1:]
            df.reset_index(drop=True, inplace=True)
                
        return df

    def _load_xls(self, path, sheet_name=None):
        self._load_excel(path, sheet_name)

    def _load_pdf(self, path):
        reader = PdfReader(path)
        self.headers = ["Page", "Content"]
        self._create_table(self.headers)
        
        rows = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    rows.append((i+1, line))
        
        cols = ', '.join([f'"{h}"' for h in self.headers])
        placeholder = ','.join(['%s']*len(self.headers))
        self.cursor.executemany(f"INSERT INTO {self.table_name} ({cols}) VALUES ({placeholder})", rows)
        self.conn.commit()

    def _deduplicate_headers(self, headers):
        seen = {}
        new_headers = []
        for h in headers:
            h = str(h).strip()
            if h in seen:
                seen[h] += 1
                new_headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                new_headers.append(h)
        return new_headers

    def _create_table(self, headers):
        cols = [f'"{h}" TEXT' for h in headers]
        cols.insert(0, 'id SERIAL PRIMARY KEY')
        try:
            self.cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            self.conn.commit()
        except Exception:
            pass
            
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} ({', '.join(cols)})")
        self.conn.commit()

    def get_preview(self, limit=None):
        """Returns a preview of the raw data (default: all rows)"""
        try:
            if not self.headers:
                self._recover_raw_headers()
                
            self.cursor.execute(f"SELECT id, * FROM {self.table_name}")
            rows = self.cursor.fetchall()
            
            rows = [list(r) for r in rows] 
            
            headings = ['_id'] + self.headers
            
            return {"headers": headings, "rows": rows}
        except Exception:
            return {"headers": [], "rows": []}

    def delete_raw_rows(self, row_ids):
        """Deletes rows from raw_data based on list of row_ids."""
        if not row_ids: return False
        
        placeholders = ','.join(['%s']*len(row_ids))
        self.cursor.execute(f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})", row_ids)
        self.conn.commit()
        return True

def set_raw_header(self, row_id):
        """Sets the specified row as header, deletes previous rows, and recreates table."""
        # 1. Get the new header row content
        # Skip the id column (first column returned by SELECT *)
        self.cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = %s", (row_id,))
        # We need to fetch columns excluding the serial ID.
        # Since SELECT * includes ID, we need to slice.
        # Actually, easier to query column names dynamically or assume order.
        # Let's just fetch and discard first element if we can't easily query specific cols.
        # Better: SELECT col1, col2... but we don't know them yet.
        # Let's fetch all, then remove first item (id).
        
        # Wait, to be robust, let's use the headers we already have in memory!
        # Or query information_schema.
        
        # For now, let's do the simple fetch and slice, assuming headers are synced or we reconstruct.
        # If the table is empty, we can't do this.
        
        # Let's assume headers are in memory `self.headers`
        if not self.headers:
             self._recover_raw_headers()
             
        # Use standard offset. 
        # But we need the actual row content.
        # Let's construct query dynamically.
        if self.headers:
            cols_str = ', '.join([f'"{h}"' for h in self.headers])
            self.cursor.execute(f"SELECT {cols_str} FROM {self.table_name} WHERE id = %s", (row_id,))
            new_header_row = self.cursor.fetchone()
        else:
            # Fallback to slice if headers missing
            self.cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = %s", (row_id,))
            res = self.cursor.fetchone()
            if res: new_header_row = res[1:] # Skip ID
            else: new_header_row = None

        if not new_header_row:
             raise ValueError("Row not found.")
             
        # 2. Get all data rows AFTER this id
        self.cursor.execute(f"SELECT id, * FROM {self.table_name} WHERE id > %s", (row_id,))
        raw_results = self.cursor.fetchall()
        
        # Extract just the data columns (skip id)
        remaining_rows = [r[1:] for r in raw_results]
        
        # 3. Clean and Deduplicate New Headers
        new_headers = [str(c).strip() if c else f"col_{i}" for i, c in enumerate(new_header_row)]
        new_headers = self._deduplicate_headers(new_headers)
        
        # 4. Recreate Table
        self.cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
        self._create_table(new_headers)
        self.headers = new_headers # Update instance state
        
        # 5. Insert Remaining Data
        if remaining_rows:
            placeholder = ','.join(['%s']*len(new_headers))
            cols = ', '.join([f'"{h}"' for h in new_headers])
            self.cursor.executemany(f"INSERT INTO {self.table_name} ({cols}) VALUES ({placeholder})", remaining_rows)
            
        self.conn.commit()
        return True

    def close(self):
        self.conn.close()

    def get_unique_values(self, column_name):
        """Returns all unique values for a specific column in the raw_data table."""
        if not column_name:
            return []
        
        try:
            # Column names are quoted to handle spaces/special chars
            query = f'SELECT DISTINCT "{column_name}" FROM {self.table_name} WHERE "{column_name}" IS NOT NULL'
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            return [str(row[0]) for row in results if row[0] is not None]
        except Exception as e:
            print(f"Error fetching unique values: {e}")
            return []

    def filter_raw_data(self, column_name, filter_value):
        """Keeps only rows matching the filter_value in the specified column, removing all others."""
        if not column_name:
            return False
        
        try:
            # Delete all rows where the column does not match the filter_value
            # We use != for standard filtering, or IS NOT if filter_value is None
            if filter_value is None:
                query = f'DELETE FROM {self.table_name} WHERE "{column_name}" IS NOT NULL'
            else:
                query = f'DELETE FROM {self.table_name} WHERE "{column_name}" != %s'
            
            self.cursor.execute(query, (filter_value,) if filter_value is not None else ())
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error filtering raw data: {e}")
            return False
