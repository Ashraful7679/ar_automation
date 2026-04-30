import subprocess
import hashlib
import os
import sys
import json
import base64
from datetime import datetime, timedelta

class HardwareID:
    @staticmethod
    def get_hwid():
        """
        Generates a unique hardware ID based on CPU, Motherboard, and Disk serials using PowerShell.
        """
        try:
            def run_ps(cmd):
                return subprocess.check_output(['powershell', '-Command', cmd], shell=True).decode().strip()

            # CPU Serial
            cpu = run_ps("(Get-CimInstance Win32_Processor).ProcessorId")
            # Motherboard Serial
            board = run_ps("(Get-CimInstance Win32_BaseBoard).SerialNumber")
            # Disk Serial (System Drive - usually first one)
            disk = run_ps("(Get-CimInstance Win32_DiskDrive | Select-Object -First 1).SerialNumber")
            
            raw_id = f"{cpu}-{board}-{disk}"
            # Create a clean hash
            hwid_hash = hashlib.sha256(raw_id.encode()).hexdigest().upper()
            # Return first 16 chars in 4x4 blocks for readability
            return "-".join([hwid_hash[i:i+4] for i in range(0, 16, 4)])
        except Exception as e:
            print(f"Error generating HWID: {e}")
            return "ERR-HWID-0000"

class LicenseManager:
    LICENSE_FILE = "license.dat"
    SECRET_KEY = "AR-AUTOMATION-SECRET-2024" # In a real app, this would be more complex

    @classmethod
    def generate_key(cls, hwid, expiry_days=365):
        """
        Generates an obfuscated license key.
        """
        expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime("%Y-%m-%d")
        payload = f"{hwid}|{expiry_date}"
        signature = hashlib.sha256((payload + cls.SECRET_KEY).encode()).hexdigest()[:8]
        raw_key = f"{payload}|{signature}"
        return base64.b64encode(raw_key.encode()).decode()

    @classmethod
    def verify_license(cls, key_b64):
        """
        Verifies the obfuscated license key against the current machine's HWID and expiry.
        """
        try:
            # Decode the obfuscated key
            key_string = base64.b64decode(key_b64.encode()).decode()
            parts = key_string.split('|')
            if len(parts) != 3:
                return False, "Invalid Key Format"

            key_hwid, key_expiry, key_signature = parts
            current_hwid = HardwareID.get_hwid()

            # 1. Check HWID
            if key_hwid != current_hwid:
                return False, "License is bound to another machine"

            # 2. Check Signature
            expected_sig = hashlib.sha256((f"{key_hwid}|{key_expiry}" + cls.SECRET_KEY).encode()).hexdigest()[:8]
            if key_signature != expected_sig:
                return False, "Tampered License Key"

            # 3. Check Expiry
            expiry_dt = datetime.strptime(key_expiry, "%Y-%m-%d")
            if datetime.now() > expiry_dt:
                return False, f"License expired on {key_expiry}"

            return True, f"Valid until {key_expiry}"
        except Exception as e:
            return False, f"Verification Error: {str(e)}"

    @classmethod
    def save_license(cls, key_string):
        with open(cls.LICENSE_FILE, "w") as f:
            f.write(key_string)

    @classmethod
    def load_license(cls):
        if os.path.exists(cls.LICENSE_FILE):
            with open(cls.LICENSE_FILE, "r") as f:
                return f.read().strip()
        return None
