import pdfplumber
import sys
import os

file_path = r"e:\Completed Projects\AR_Automation\uploads\BSH AR SHARON\Healix\HEALIX.pdf"

with pdfplumber.open(file_path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n--- PAGE {i} (FULL TEXT) ---")
        print(page.extract_text())
