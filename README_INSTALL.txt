ONE-CLICK INSTALLATION GUIDE
============================

1. Locate the Executable:
   - Go to the "dist" folder inside "AR_Automation".
   - You will find "AR_Automation.exe".

2. Installation:
   - This makes a "Portable" installation.
   - Creates a new folder anywhere on your computer (e.g., C:\AR_System or Desktop\AR_App).
   - Copy "AR_Automation.exe" into that folder.

3. Running the App:
   - Double-click "AR_Automation.exe".
   - A black console window will open (this is the server). NOTIFY: Do not close this window while using the app.
   - Open your web browser and go to: http://127.0.0.1:5000
   - (Or check the console window for the address).

4. Data Usage:
   - On first run, it will automatically create:
     * ar_system.db (User Accounts)
     * session_v2.db (Temporary Processing Data)
     * uploads/ (Folder for uploaded files)
     * output/ (Folder for generated exports)
   - These files/folders will appear next to the .exe file.

5. Uninstall:
   - Simply delete the folder containing the .exe and the created files.

TROUBLESHOOTING:
- If it fails to start, ensure no other application is using port 5000.
- If you see "Permission Denied", try running as Administrator (rarely needed).
