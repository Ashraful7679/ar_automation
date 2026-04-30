import pdfplumber

file_path = r"e:\Completed Projects\AR_Automation\uploads\BSH AR SHARON\Healix\HEALIX.pdf"

with pdfplumber.open(file_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    for w in words:
        if "AOP082309428" in w['text'] or "26.72" in w['text']:
            print(f"Text: {w['text']}, Top: {w['top']}, Bottom: {w['bottom']}, X0: {w['x0']}")
