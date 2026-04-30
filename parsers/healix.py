import pdfplumber
import re

from pdf2image import convert_from_path
from collections import defaultdict
from parsers.base import BaseParser
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class HealixParser(BaseParser):
    def __init__(self):
        self.raw_headers = ["Date", "Ref", "Description", "Debit", "Remitted"]
        self.formatted_headers = [
            "Sl. No", "Inv No", "Date", "Patient ID", "Patient Name",
            "Invoice Balance", "Amt To Adjust", "CustomerCode",
            "Remark 1", "Remark 2", "Remark 3"
        ]

        self.pattern = re.compile(
            r'(?P<date>\d{2}/\d{2}/\d{4})\s+'
            r'(?P<type>INV)\s+'
            r'(?P<ref>[A-Z]{3}\d{6,})\s+'
            r'(?P<desc>.+?)\s+'
            r'(?P<debit>[\d,\.]+)\s+'
            r'(?P<credit>[\d,\.]+)\s+'
            r'(?P<remitted>[\d,\.]+)'
        )

    # ---------------------------
    # 🔹 TEXT EXTRACTION (PRIMARY)
    # ---------------------------
    def extract_with_pdfplumber(self, page):
        words = page.extract_words(
            x_tolerance=2,
            y_tolerance=2,
            keep_blank_chars=False
        )

        if not words:
            return []

        # Group words by Y coordinate with tolerance to handle minor misalignments
        # Cluster words that are within 5 units of each other vertically
        lines_data = []
        for w in sorted(words, key=lambda x: x['top']):
            y = w['top']
            found = False
            for line in lines_data:
                # If word is within 5 units of an existing line's average Y
                if abs(y - line['y']) < 5:
                    line['words'].append(w)
                    # Update average Y slightly
                    line['y'] = (line['y'] * (len(line['words'])-1) + y) / len(line['words'])
                    found = True
                    break
            if not found:
                lines_data.append({'y': y, 'words': [w]})

        final_lines = []
        for line in lines_data:
            # Sort words in each line by X coordinate
            sorted_words = sorted(line['words'], key=lambda x: x['x0'])
            final_lines.append(" ".join(w['text'] for w in sorted_words))

        return final_lines

    # ---------------------------
    # 🔹 OCR FALLBACK (SECONDARY)
    # ---------------------------
    def extract_with_ocr(self, file_path, page_number):
        try:
            images = convert_from_path(file_path, first_page=page_number+1, last_page=page_number+1)
            text = pytesseract.image_to_string(images[0])
            return text.split("\n")
        except Exception as e:
            print(f"OCR Error: {e}")
            return []

    # ---------------------------
    # 🔹 MAIN PARSE
    # ---------------------------
    def parse(self, file_path):
        rows = []

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                lines = self.extract_with_pdfplumber(page)

                # 🔥 Detect missing data (critical check)
                if not any("INV" in l for l in lines):
                    print(f"DEBUG: No INV lines found on page {i}, trying OCR fallback...")
                    lines = self.extract_with_ocr(file_path, i)

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # skip noise
                    if "INV" not in line:
                        continue
                    if "BHD" in line:
                        continue
                    if "Total Value" in line:
                        continue

                    # fix merged date issue (e.g. AmountDate)
                    line = re.sub(
                        r'(\d+\.\d{2})(\d{2}/\d{2}/\d{4})',
                        r'\1 \2',
                        line
                    )

                    match = self.pattern.search(line)
                    if match:
                        d = match.groupdict()
                        rows.append((
                            d["date"],
                            d["ref"],
                            d["desc"].strip(),
                            d["debit"],
                            d["remitted"]
                        ))
        return rows

    # ---------------------------
    # 🔹 TRANSFORM
    # ---------------------------
    def transform(self, raw_data):
        output = []
        for idx, row in enumerate(raw_data):
            desc = row[2]
            # Name Logic: "Patient Name, Unknown" -> "Patient Name"
            patient_name = desc.split(",")[0].strip() if "," in desc else desc

            output.append([
                idx + 1,            # Sl. No
                row[1],             # Inv No (Ref)
                row[0],             # Date
                "",                 # Patient ID
                patient_name,       # Patient Name
                row[3].replace(",", ""), # Invoice Balance (Debit)
                row[4].replace(",", ""), # Amt To Adjust (Remitted)
                "",                 # CustomerCode
                "",                 # Remark 1
                "",                 # Remark 2
                ""                  # Remark 3
            ])

        return self.formatted_headers, output