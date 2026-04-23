
import PyInstaller.__main__
import os
import shutil

# Clean build artifacts
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

PyInstaller.__main__.run([
    'main.py',
    '--name=AR_Automation',
    '--onefile',
    '--console',  # Keep console to allow user to close the app easily
    '--add-data=templates;templates',
    '--add-data=static;static',
    '--hidden-import=pypdf',
    '--hidden-import=fpdf',
    '--hidden-import=openpyxl',
    '--hidden-import=xlrd',
    '--hidden-import=pandas',
    '--hidden-import=sqlalchemy',
    '--hidden-import=flask_sqlalchemy',
    '--hidden-import=flask_login',
    '--hidden-import=engineio.async_drivers.threading',
    '--clean',
])
