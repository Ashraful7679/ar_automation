import pdfplumber
import sys
import os

file_path = r"e:\Completed Projects\AR_Automation\uploads\BSH AR SHARON\Healix\HEALIX.pdf"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

with pdfplumber.open(file_path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n--- PAGE {i} (TEXT) ---")
        text = page.extract_text()
        print(text)
        
        print(f"\n--- PAGE {i} (WORDS) ---")
        words = page.extract_words()
        for w in words[:20]: # Show first 20 words
            print(w['text'], end=' ')
        print("\n...")
