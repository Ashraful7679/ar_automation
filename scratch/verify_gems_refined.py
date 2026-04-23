
import sys
import os
import re

# Mock the BaseParser if needed, or just import
sys.path.insert(0, os.path.abspath('.'))
from parsers.gems import GemsParser

def debug_gems_refined():
    parser = GemsParser()
    
    # Mock text that represents the GEMS multi-line, remarks, noise, and split invoices
    # Sample 1: The user's split invoice example
    # AOP1124
    # 10330/AO
    # P1124103
    # 50
    # + Pat File No (225616)
    
    sample_text = """
21/11/2024 AOP1124
10330/AO
P1124103
50
225616 SIBAL MUHAMMAD SAEED BUTT
20018517-05 40.210 0.000 0.000 0.000 0.000 5.000 35.210 0.000 0
Remarks : Coverage confirmed.

22/11/2024 AIP1124
05/02/20259200202500099
06677
123456 JOHN DOE
20018517-06 100.000 0.000 0.000 0.000 0.000 0.000 100.000 0.000 0
"""
    
    # We need to mock pdfplumber page.extract_text()
    class MockPage:
        def __init__(self, text):
            self.text = text
        def extract_text(self):
            return self.text

    class MockPDF:
        def __init__(self, text):
            self.pages = [MockPage(text)]
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    import pdfplumber
    original_open = pdfplumber.open
    pdfplumber.open = lambda path: MockPDF(sample_text)

    try:
        raw_rows = parser.parse("dummy_path")
        print(f"Total Raw Rows extracted: {len(raw_rows)}")
        
        headers, formatted = parser.transform(raw_rows)
        for i, fr in enumerate(formatted):
            print(f"\n--- Row {i+1} ---")
            for h, v in zip(headers, fr):
                print(f"{h:15}: {v}")
            
    finally:
        pdfplumber.open = original_open

if __name__ == "__main__":
    debug_gems_refined()
