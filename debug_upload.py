import sys
import os
import pandas as pd
sys.path.append(os.getcwd())
from AR_Automation.logic_engine import LogicEngine

file_path = r"D:\BrainyFlavors\File Conversion Soft\Input and Output files\Input files\ERROR500.XLSX"

print(f"Testing load for: {file_path}")

try:
    engine = LogicEngine()
    engine.load_file(file_path)
    print("SUCCESS: File loaded.")
    print("Headers:", engine.headers)
except Exception as e:
    print("FAILURE: File load failed.")
    import traceback
    traceback.print_exc()
