import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsers.gems import GemsParser

class TestGemsBugs(unittest.TestCase):
    def test_extra_zero_and_trailing_digit(self):
        print("\n--- Testing Extra Zero and Trailing Digit Bugs ---")
        parser = GemsParser()
        
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            
            # Row 1: Split Invoice with intervening "0"
            # AOP1234 (Line 1) ... 0 ... (Next Line) 55555
            # We insert \n to trigger "Force Suffix" logic
            
            # Row 2: Full Invoice Logic with trailing "4"
            # AOP5678, PatID=88888, Tail=99999, PageNum=4
            
            text = (
                "01/01/2024 AOP1234 0 \n 55555 John Doe 100.00\n"
                "02/01/2024 AOP5678 88888 99999 4 200.00"
            )
            
            mock_page.extract_text.return_value = text
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            rows = parser.parse("dummy.pdf")
            
            # Check Row 1
            if len(rows) > 0:
                inv1 = rows[0][1]
                print(f"Row 1 Inv: {inv1}")
                self.assertEqual(len(inv1), 12, "Row 1 should be 12 chars (AOP+4+5)")
                self.assertTrue(inv1.endswith("55555"), "Row 1 should capture 55555 as tail")
            
            # Check Row 2
            if len(rows) > 1:
                inv2 = rows[1][1]
                print(f"Row 2 Inv: {inv2}")
                self.assertFalse(inv2.endswith("4"), "Row 2 should ignoring trailing '4'")
                self.assertEqual(len(inv2), 12, "Row 2 should be 12 chars")
                self.assertTrue(inv2.endswith("99999"), "Row 2 should end with 99999")

if __name__ == "__main__":
    unittest.main()
