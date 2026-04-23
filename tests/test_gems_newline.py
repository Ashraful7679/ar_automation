import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.gems import GemsParser

class TestGemsNewlineLogic(unittest.TestCase):
    def test_split_invoice_newline(self):
        print("\n--- Testing Split Invoice with Newlines ---")
        parser = GemsParser()
        
        # Mock pdfplumber open context manager
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            
            # Scenario 1: Date, AOP1234, PatID(55555), ^NL^, Tail(67890)
            # Result: Inv=AOP...67890, PatID=55555
            # We construct text that produces these tokens
            # "01/01/2024" "AOP1234" "55555" "\n" "67890"
            mock_page.extract_text.return_value = "01/01/2024 AOP1234 55555\n67890 John Doe 123-456 100.00"
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            rows = parser.parse("dummy.pdf")
            if not rows:
                print("FAIL: No rows returned")
                return

            # check first row
            # Row index 1 is Inv, 2 is PatID
            inv = rows[0][1]
            pat_id = rows[0][2]
            
            print(f"Case 1 (Pat SameLine, Tail NextLine): Inv={inv}, PatID={pat_id}")
            
            # Expect Inv to end in 67890
            self.assertTrue(inv.endswith("67890"), "Invoice should include tail from next line")
            self.assertEqual(pat_id, "55555", "PatID should be from same line")

    def test_split_invoice_newline_case2(self):
        # Scenario 2: Date, AOP1234, ^NL^, Tail(67890), PatID(55555)
        # Result: Inv=AOP...67890, PatID=55555 (Because Tail forced)
        print("\n--- Testing Case 2 (Tail NextLine, PatID Same/Next) ---")
        parser = GemsParser()
        
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            
            # "01/01/2024" "AOP1234" "\n" "67890" "55555"
            mock_page.extract_text.return_value = "01/01/2024 AOP1234\n67890 55555 John Doe 123-456 200.00"
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            rows = parser.parse("dummy.pdf")
            inv = rows[0][1]
            pat_id = rows[0][2]
            
            print(f"Case 2 (Head line 1, Tail line 2): Inv={inv}, PatID={pat_id}")
            
            self.assertTrue(inv.endswith("67890"), "Invoice should include tail from next line")
            self.assertEqual(pat_id, "55555", "PatID should be captured after tail")

if __name__ == "__main__":
    unittest.main()
