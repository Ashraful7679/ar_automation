"""
Test script for Worldwide Insurance parser
"""
import sys
import os
import unittest

sys.path.insert(0, r'D:\BrainyFlavors\File Conversion Soft\AR_Automation')

from parsers.worldwide import WorldwideParser

def test_worldwide_parser():
    print("="*80)
class TestWorldwideParser(unittest.TestCase):
    def setUp(self):
        self.parser = WorldwideParser()
        # Sample raw data mirroring the 14 columns extracted from PDF
        # Columns: 
        # 0: PATIENT NAME, 1: DOB, 2: CLAIM ID, 3: DATE OF SERVICE, 
        # 4: CHARGE, 5: ALLOWED, 6: PATIENT RESP, 7: CO-PAY, 
        # 8: COINSURANCE, 9: DEDUCTIBLE, 10: INELIGIBLE, 11: REMARK, 
        # 12: PAID PROVIDER, 13: INVOICE NUMBER
        self.sample_raw_data = [
            [
                "JOHN DOE", "01/01/1980", "CID12345", "12/12/2025",
                "200.00", "150.00", "10.00", "20.00",
                "0.00", "0.00", "50.00", "R1",
                "BHD 140.00", "INV-001"
            ],
            [
                "JANE SMITH", "02/02/1990", "CID67890", "12/13/2025",
                "300.00", "280.00", "20.00", "0.00",
                "0.00", "0.00", "20.00", "R2",
                "280.00", "INV-002"
            ]
        ]

    def test_transform_match_headers(self):
        """Test if transform returns correct number of columns and matches standard headers"""
        headers, rows = self.parser.transform(self.sample_raw_data)
        
        # Check headers match standard headers
        expected_headers = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remarks"]
        self.assertEqual(headers, expected_headers)
        
        # Check row count
        self.assertEqual(len(rows), 2)
        
        # Check column count
        self.assertEqual(len(rows[0]), len(expected_headers))

    def test_transform_mapping(self):
        """Test if data is mapped to correct columns"""
        headers, rows = self.parser.transform(self.sample_raw_data)
        
        # Row 1 Checks
        row1 = rows[0]
        self.assertEqual(row1[1], "INV-001")        # Inv No
        self.assertEqual(row1[2], "12/12/2025")     # Date
        self.assertEqual(row1[3], "CID12345")       # Patient ID
        self.assertEqual(row1[4], "JOHN DOE")       # Patient Name
        self.assertEqual(row1[5], "140.00")         # Invoice Balance (BHD removed)
        self.assertEqual(row1[6], "50.00")          # Amt To Adjust (Ineligible)
        self.assertEqual(row1[8], "R1")             # Remark 1

    def test_bhd_removal_in_transform(self):
        """Test if BHD is removed from Amount column"""
        # Note: BHD is primarily removed in parse(), but transform also has a safety check
        headers, rows = self.parser.transform(self.sample_raw_data)
        
        # Check Row 1 (had "BHD 140.00")
        self.assertEqual(rows[0][5], "140.00")
        
        # Check Row 2 (had "280.00")
        self.assertEqual(rows[1][5], "280.00")

    def test_parse_structure(self):
        """
        Verify that parse() can handle a real file (or at least doesn't crash)
        and returns list of lists.
        """
        pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'
        if os.path.exists(pdf_path):
            rows = self.parser.parse(pdf_path)
            # We assume the file has valid data, so rows should not be empty
            # But even if it is, it should be a list
            self.assertIsInstance(rows, list)
            if rows:
                self.assertIsInstance(rows[0], list)
                # Verify we are getting 14 columns
                self.assertTrue(len(rows[0]) >= 14, f"Expected at least 14 columns, got {len(rows[0])}")
        else:
            self.skipTest("Sample PDF not found")

if __name__ == '__main__':
    unittest.main()
