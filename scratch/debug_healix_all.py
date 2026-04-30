import pdfplumber

file_path = r"e:\Completed Projects\AR_Automation\uploads\BSH AR SHARON\Healix\HEALIX.pdf"

with pdfplumber.open(file_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
