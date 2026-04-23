"""
Test script for PayAdvice parser
"""
import sys
sys.path.insert(0, r'D:\BrainyFlavors\File Conversion Soft\AR_Automation')

from parsers.payadvice import PayAdviceParser

def test_payadvice_parser():
    print("="*80)
    print("TESTING PAYADVICE PARSER")
    print("="*80)
    
    parser = PayAdviceParser()
    pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'
    
    print("\n1. Testing parse() method...")
    try:
        raw_data = parser.parse(pdf_path)
        print(f"   ✓ Successfully extracted {len(raw_data)} rows")
        print(f"   Raw headers: {parser.raw_headers}")
        print("\n   Sample raw data (first 3 rows):")
        for i, row in enumerate(raw_data[:3], 1):
            print(f"   {i}. {row}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n2. Testing transform() method...")
    try:
        # Simulate raw_data with rowid (as it comes from SQLite)
        simulated_data = [[i] + row for i, row in enumerate(raw_data)]
        
        headers, formatted_data = parser.transform(simulated_data)
        print(f"   ✓ Successfully transformed {len(formatted_data)} rows")
        print(f"   Formatted headers: {headers}")
        print("\n   Sample formatted data (first 3 rows):")
        for i, row in enumerate(formatted_data[:3], 1):
            print(f"   {i}. {row}")
        
        # Verify BHD removal
        print("\n3. Verifying BHD currency removal...")
        bhd_found = False
        for row in formatted_data:
            invoice_balance = str(row[5])  # Index 5 is Invoice Balance
            if 'BHD' in invoice_balance.upper():
                bhd_found = True
                print(f"   ✗ BHD still present in: {row}")
        
        if not bhd_found:
            print("   ✓ BHD successfully removed from all amounts")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_payadvice_parser()
    print("\n" + "="*80)
    print(f"TEST {'PASSED' if success else 'FAILED'}")
    print("="*80)
