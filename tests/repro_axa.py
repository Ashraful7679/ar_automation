import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsers.axa_ppp import AxaPppParser

class TestAxaRepro(unittest.TestCase):
    def test_axa_parsing(self):
        print("\n--- Testing AXA Parsing with User Sample ---")
        parser = AxaPppParser()
        
        # Sample text provided by user
        # Note: formatting in PDF extract might vary (tabs vs spaces)
        # Assuming space separation for now as regex relies on \s+
        
        sample_text = (
            "Patient name Your invoice number Our invoice ID Amount invoiced Amount paid See note\n"
            "Walid Rifat Mahmoud OP05037625 75215441 BHD 27.94 BHD 20.00\n"
            "Walid Rifat Mahmoud OP05037625-EX-GRATIA 75215454 BHD 7.94 BHD 7.94\n"
            "Walid Rifat Mahmoud OP05152725 75215483 BHD 34.15 BHD 20.00\n"
            "Walid Rifat Mahmoud OP05152725-EX-GRATIA 75215495 BND 14.15 BHD 4.06"
        )
        
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = sample_text
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            # 1. Parse Raw
            raw_rows = parser.parse("dummy.pdf")
            print(f"Raw Parsed: {len(raw_rows)} rows")
            for r in raw_rows:
                print(r)
            
            # 2. Transform
            headers, formatted_rows = parser.transform(raw_rows)
            print("\nFormatted Rows:")
            for fr in formatted_rows:
                print(fr)
                
            # validations
            if len(formatted_rows) < 4:
                print("FAIL: Expected 4 rows")
                return

            row1 = formatted_rows[0]
            # Exp: Sl, Inv(10), Date(Blank), PatID(Blank), Name, Bal, Adj, Code, Rem
            self.assertEqual(row1[1], "OP05037625")
            self.assertEqual(row1[2], "") # Date Blank
            self.assertEqual(row1[4], "Walid Rifat Mahmoud")
            self.assertEqual(row1[5], "27.94")
            self.assertEqual(row1[6], "20.00")
            self.assertEqual(row1[8], "") # No Remark

            row2 = formatted_rows[1]
            # Inv: OP05037625-EX-GRATIA -> Inv: OP05037625, Rem: EX-GRATIA
            self.assertEqual(row2[1], "OP05037625") 
            self.assertEqual(row2[8], "EX-GRATIA")
            
            # Row 4: BND currency?
            row4 = formatted_rows[3]
            self.assertEqual(row4[5], "14.15")

if __name__ == "__main__":
    unittest.main()
