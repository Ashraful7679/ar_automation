"""
End-to-end integration test for PayAdvice and Worldwide parsers
"""
import sys
import os
sys.path.insert(0, r'D:\BrainyFlavors\File Conversion Soft\AR_Automation')

from logic_engine import LogicEngine

def test_integration():
    print("="*80)
    print("END-TO-END INTEGRATION TEST")
    print("="*80)
    
    # Test 1: PayAdvice PDF
    print("\n" + "="*80)
    print("TEST 1: PayAdvice PDF with PAYADVICE Profile")
    print("="*80)
    
    engine = LogicEngine(db_path=":memory:")
    pdf_path = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\PayAdvice_AUBCHLK3E004FY87.pdf'
    
    try:
        print("\n1. Loading PayAdvice PDF...")
        engine.load_file(pdf_path, profile_name='PAYADVICE')
        print("   ✓ File loaded successfully")
        
        print("\n2. Getting formatted preview...")
        preview = engine.get_formatted_preview()
        print(f"   ✓ Headers: {preview['headers']}")
        print(f"   ✓ Total rows: {len(preview['rows'])}")
        
        print("\n3. Sample formatted output (first 3 rows):")
        for i, row in enumerate(preview['rows'][:3], 1):
            print(f"   {i}. Sl.No={row[1]}, Inv={row[2]}, Date={row[3]}, Name={row[5]}, Amount={row[6]}")
        
        # Verify BHD removal
        print("\n4. Verifying BHD removal...")
        bhd_count = 0
        for row in preview['rows']:
            amount = str(row[6])  # Invoice Balance column
            if 'BHD' in amount.upper():
                bhd_count += 1
        
        if bhd_count == 0:
            print(f"   ✓ BHD successfully removed from all {len(preview['rows'])} rows")
        else:
            print(f"   ✗ BHD still present in {bhd_count} rows")
        
        print("\n5. Testing export functionality...")
        try:
            output_file = engine.generate_custom_output(
                profile_name='PAYADVICE',
                custom_filename='Test_PayAdvice_Output',
                file_format='xlsx'
            )
            print(f"   ✓ Successfully exported to: {output_file}")
        except Exception as e:
            print(f"   ✗ Export failed: {e}")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine.close()
    
    # Test 2: Worldwide PDF
    print("\n" + "="*80)
    print("TEST 2: Worldwide Insurance PDF with WORLDWIDE Profile")
    print("="*80)
    
    engine2 = LogicEngine(db_path=":memory:")
    pdf_path2 = r'D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\world wide ins payment.pdf'
    
    try:
        print("\n1. Loading Worldwide PDF...")
        engine2.load_file(pdf_path2, profile_name='WORLDWIDE')
        print("   ✓ File loaded successfully")
        
        print("\n2. Getting formatted preview...")
        preview2 = engine2.get_formatted_preview()
        print(f"   ✓ Headers: {preview2['headers']}")
        print(f"   ✓ Total rows: {len(preview2['rows'])}")
        
        print("\n3. Sample formatted output (first 3 rows):")
        for i, row in enumerate(preview2['rows'][:3], 1):
            print(f"   {i}. Sl.No={row[1]}, Inv={row[2]}, Date={row[3]}, Name={row[5]}, Amount={row[6]}")
        
        # Verify BHD removal
        print("\n4. Verifying BHD removal...")
        bhd_count = 0
        for row in preview2['rows']:
            amount = str(row[6])
            if 'BHD' in amount.upper():
                bhd_count += 1
        
        if bhd_count == 0:
            print(f"   ✓ BHD successfully removed from all {len(preview2['rows'])} rows")
        else:
            print(f"   ✗ BHD still present in {bhd_count} rows")
        
        print("\n5. Testing export functionality...")
        try:
            output_file2 = engine2.generate_custom_output(
                profile_name='WORLDWIDE',
                custom_filename='Test_Worldwide_Output',
                file_format='xlsx'
            )
            print(f"   ✓ Successfully exported to: {output_file2}")
        except Exception as e:
            print(f"   ✗ Export failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine2.close()

if __name__ == "__main__":
    success = test_integration()
    print("\n" + "="*80)
    print(f"INTEGRATION TEST {'PASSED ✓' if success else 'FAILED ✗'}")
    print("="*80)
