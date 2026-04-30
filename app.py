
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, redirect, url_for, session
import os
import shutil
import time
import pandas as pd
from logic_engine import LogicEngine
import traceback
import sys
from flask_login import LoginManager, login_required, current_user
from models import db, User, FileHistory
from auth_routes import auth_bp
from super_admin_routes import super_admin_bp
from licensing_utils import LicenseManager, HardwareID

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = sys._MEIPASS
    template_folder = os.path.join(RESOURCE_DIR, 'templates')
    static_folder = os.path.join(RESOURCE_DIR, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR
    app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'ar_system.db')
DB_PATH = os.path.join(BASE_DIR, 'session_v2.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
app.config['SECRET_KEY'] = SECRET_KEY

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

app.register_blueprint(auth_bp)
app.register_blueprint(super_admin_bp)

# --- SUBSCRIPTION MIDDLEWARE ---
@app.before_request
def check_subscription():
    # Allow access to static, super-admin, and auth routes
    if request.path.startswith('/static') or \
       request.path.startswith('/super-admin') or \
       request.path.startswith('/login') or \
       request.path.startswith('/logout') or \
       request.path.startswith('/subscription-status') or \
       not current_user.is_authenticated:
        return

    # Super admin doesn't have quotas
    if session.get('is_super_admin'):
        return

    # Reset daily quota if it's a new day
    if current_user.reset_daily_quota():
        db.session.commit()
    reason = None
    if current_user.expiry_date and datetime.now() > current_user.expiry_date:
        reason = "Account Expired"
    elif current_user.total_quota != -1 and current_user.used_quota >= current_user.total_quota:
        reason = "Total Quota Reached"
    elif current_user.daily_quota != -1 and current_user.used_today >= current_user.daily_quota:
        reason = "Daily Quota Reached"

    if reason:
        if request.path.startswith('/api/'):
            return jsonify({"error": f"Subscription Blocked: {reason}"}), 403
        return render_template('subscription_expired.html', reason=reason)

@app.route('/subscription-status')
@login_required
def subscription_status():
    current_user.reset_daily_quota()
    db.session.commit()
    
    return jsonify({
        "expiry_date": current_user.expiry_date.strftime("%Y-%m-%d") if current_user.expiry_date else "Permanent",
        "days_left": (current_user.expiry_date - datetime.now()).days if current_user.expiry_date else 9999,
        "total_quota": current_user.total_quota,
        "used_quota": current_user.used_quota,
        "daily_quota": current_user.daily_quota,
        "used_today": current_user.used_today,
        "remaining_total": (current_user.total_quota - current_user.used_quota) if current_user.total_quota != -1 else 9999,
        "remaining_today": (current_user.daily_quota - current_user.used_today) if current_user.daily_quota != -1 else 9999
    })

# Create DB and Default Admin
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Default 'admin' user created.")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user)

@app.route('/api/get_sheets', methods=['POST'])
def get_sheets():
    """Get sheet names from uploaded Excel file"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        # Check if it's an Excel file
        if not (file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls') or file.filename.lower().endswith('.xlsm')):
            return jsonify({"sheets": [], "is_excel": False})
        
        # Fixed filename to avoid accumulation
        filename = file.filename
        name, ext = os.path.splitext(filename)
        unique_filename = f"current_upload_meta{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        # Get sheet names
        import pandas as pd
        
        # Try without engine first (auto-detect), works for most files
        try:
            xl_file = pd.ExcelFile(filepath)
            sheet_names = xl_file.sheet_names
            xl_file.close()
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for SpreadsheetML XML (BUPA)
            with open(filepath, 'rb') as f:
                header_check = f.read(512).decode('utf-8', errors='ignore')
            
            if '<?xml' in header_check[:200] and 'spreadsheet' in header_check.lower():
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    ns = {'x': 'urn:schemas-microsoft-com:office:spreadsheet'}
                    worksheets = root.findall('.//x:Worksheet', ns)
                    sheet_names = [ws.get('{urn:schemas-microsoft-com:office:spreadsheet}Name', f'Sheet{i+1}') 
                                   for i, ws in enumerate(worksheets)]
                    if not sheet_names: sheet_names = ['Sheet1']
                except Exception as xml_err:
                    print(f"SpreadsheetML parse in get_sheets failed: {xml_err}")
                    sheet_names = ['Sheet1']
            
            # If error is related to file format, try alternatives
            elif 'zip' in error_msg or 'xml' in error_msg or 'not a zip' in error_msg or 'cannot determine' in error_msg:
                # Try as CSV first
                try:
                    df = pd.read_csv(filepath)
                    sheet_names = ['Sheet1']  # CSV has only one sheet
                except:
                    # Try as HTML/XML (lxml not available, use built-in html.parser)
                    try:
                        from html.parser import HTMLParser
                        # Check if it's XML/HTML
                        if '<html' in header_check.lower() or '<?xml' in header_check.lower():
                            dfs = pd.read_html(filepath, flavor='html.parser')
                            sheet_names = [f'Table {i+1}' for i in range(len(dfs))]
                        else:
                            raise Exception("Not XML/HTML")
                    except Exception as xml_err:
                        # Try xlrd as last resort
                        try:
                            xl_file = pd.ExcelFile(filepath, engine='xlrd')
                            sheet_names = xl_file.sheet_names
                            xl_file.close()
                        except:
                            raise Exception(f"Could not read file: {e}")
            else:
                # Try with openpyxl
                try:
                    xl_file = pd.ExcelFile(filepath, engine='openpyxl')
                    sheet_names = xl_file.sheet_names
                    xl_file.close()
                except:
                    # Try xlrd
                    try:
                        xl_file = pd.ExcelFile(filepath, engine='xlrd')
                        sheet_names = xl_file.sheet_names
                        xl_file.close()
                    except:
                        raise Exception(f"Could not read file: {e}")
        
        return jsonify({"sheets": sheet_names, "is_excel": True, "filename": file.filename})
    except Exception as e:
        with open("error.log", "a") as f:
            f.write(f"--- get_sheets error at {os.path.basename(filepath) if 'filepath' in locals() else 'unknown'} ---\n")
            import traceback
            traceback.print_exc(file=f)
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        # Fixed filename to avoid accumulation
        filename = file.filename
        name, ext = os.path.splitext(filename)
        unique_filename = f"current_upload{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        profile = request.form.get('profile', 'default')
        sheet_name = request.form.get('sheet', None)
        
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pdf' and os.path.getsize(filepath) == 0:
            return jsonify({"error": "Invalid PDF file"}), 400
        
        engine = LogicEngine(DB_PATH)
        engine.load_file(filepath, profile_name=profile, sheet_name=sheet_name)
        
        # Cleanup uploaded file immediately after loading to DB
        try:
            os.remove(filepath)
        except:
            pass
            
        # Get both previews
        raw_preview = engine.get_preview()
        formatted_preview = engine.get_formatted_preview()
        engine.close()
        
        # Update Quotas
        current_user.used_quota += 1
        current_user.used_today += 1
        db.session.commit()
        
        return jsonify({
            "message": "File loaded successfully", 
            "raw_preview": raw_preview, 
            "formatted_preview": formatted_preview
        })
    except Exception as e:
        with open("error.log", "a") as f:
            f.write(f"--- upload error ---\n")
            import traceback
            traceback.print_exc(file=f)
        error_details = traceback.format_exc()
        return jsonify({"error": f"Upload Failed: {str(e)}", "details": error_details}), 500

def save_history(input_file, output_file, user_id=None):
    try:
        if not input_file or not output_file: return
        
        # Save to DB
        hist = FileHistory(input_filename=input_file, output_filename=output_file, user_id=user_id)
        db.session.add(hist)
        db.session.commit()
        
        # Prune > 10
        count = FileHistory.query.count()
        if count > 10:
            oldest = FileHistory.query.order_by(FileHistory.created_at.asc()).first()
            if oldest:
                db.session.delete(oldest)
                db.session.commit()
    except Exception as e:
        print(f"History Save Error: {e}")

@app.route('/api/run', methods=['POST'])
@login_required
def run_process():
    try:
        data = request.json
        profile = data.get('profile', {})
        
        engine = LogicEngine(DB_PATH)
        print(f"DEBUG: Processing with profile: {profile}")
        files = engine.generate_outputs(profile)
        print(f"DEBUG: Generated files: {files}")
        
        input_filename = "Input_File.xlsx" # Placeholder
        if files:
            save_history(input_filename, files[0], user_id=current_user.id)
            
        engine.close()
        
        return jsonify({"message": "Processing Complete. Files generated locally.", "files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/export_custom', methods=['POST'])
@login_required
def export_custom():
    try:
        data = request.json
        profile = data.get('profile', 'default')
        custom_filename = data.get('filename')
        file_format = data.get('format', 'xlsx')
        
        engine = LogicEngine(DB_PATH)
        filename = engine.generate_custom_output(profile, custom_filename, file_format)
        engine.close()
        
        save_history("Uploaded_File.xlsx", filename, user_id=current_user.id)
        
        return jsonify({'message': 'Export generated', 'file': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/combine_remarks', methods=['POST'])
@login_required
def combine_remarks():
    try:
        data = request.json
        invoice_col = data.get('invoice_col')
        remark1_col = data.get('remark1_col')
        remark2_col = data.get('remark2_col')
        remark3_col = data.get('remark3_col')
        
        if not invoice_col:
            return jsonify({"error": "Missing Invoice column selection"}), 400
            
        engine = LogicEngine(DB_PATH)
        success = engine.combine_remarks(invoice_col, remark1_col, remark2_col, remark3_col)
        
        if success:
            preview = engine.get_preview()
            engine.close()
            return jsonify({"message": "Remarks combined successfully", "preview": preview})
        else:
            engine.close()
            return jsonify({"error": "Failed to combine remarks"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_data', methods=['POST'])
def update_data():
    try:
        data = request.json
        row_id = data.get('row_id')
        col_index = data.get('col_index') 
        new_value = data.get('value')
        
        if row_id is None or col_index is None:
             return jsonify({"error": "Missing row_id or col_index"}), 400
             
        engine = LogicEngine(DB_PATH)
        success = engine.update_formatted_cell(row_id, int(col_index), new_value)
        engine.close()
        
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_data_batch', methods=['POST'])
def update_data_batch():
    try:
        data = request.json
        updates = data.get('updates')
        
        if not updates:
             return jsonify({"success": True})
             
        engine = LogicEngine(DB_PATH)
        success = engine.update_formatted_cells_batch(updates)
        engine.close()
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save_overwrite', methods=['POST'])
@login_required
def save_overwrite():
    try:
        data = request.json
        rows = data.get('rows')
        
        engine = LogicEngine(DB_PATH)
        engine.overwrite_formatted_data(rows)
        engine.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete_raw_rows', methods=['POST'])
@login_required
def delete_raw_rows():
    try:
        data = request.json
        row_ids = data.get('row_ids')
        
        engine = LogicEngine(DB_PATH)
        success = engine.delete_raw_rows(row_ids)
        engine.close()
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/set_raw_header', methods=['POST'])
@login_required
def set_raw_header():
    try:
        data = request.json
        row_id = data.get('row_id')
        
        engine = LogicEngine(DB_PATH)
        success = engine.set_raw_header(row_id)
        engine.close()
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_raw_preview', methods=['GET'])
@login_required
def get_raw_preview():
    try:
        engine = LogicEngine(DB_PATH)
        data = engine.get_preview()
        engine.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_preview', methods=['GET'])
@login_required
def get_preview():
    try:
        engine = LogicEngine(DB_PATH)
        data = engine.get_preview()
        engine.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_formatted_preview', methods=['GET'])
@login_required
def get_formatted_preview():
    try:
        engine = LogicEngine(DB_PATH)
        data = engine.get_formatted_preview()
        engine.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Settings API ---
from settings_manager import update_profile_section, get_profile_settings, load_settings, save_settings

@app.route('/api/save_settings', methods=['POST'])
@login_required
def save_settings_api():
    try:
        data = request.json
        profile = data.get('profile')
        section = data.get('section')
        config = data.get('config')
        
        if not profile or not section:
            return jsonify({"error": "Missing profile or section"}), 400
            
        update_profile_section(profile, section, config)
        return jsonify({"success": True, "message": f"Settings saved for {section}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_settings', methods=['POST'])
@login_required
def get_settings_api():
    try:
        data = request.json
        profile = data.get('profile')
        section = data.get('section')
        if not profile:
            return jsonify({"error": "Missing profile"}), 400
            
        settings = get_profile_settings(profile)
        
        if section:
            settings = settings.get(section, {})
            
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_unique_values', methods=['POST'])
@login_required
def get_unique_values():
    try:
        data = request.json
        column_name = data.get('column')
        if not column_name:
            return jsonify({"error": "Missing column name"}), 400
        
        engine = LogicEngine(DB_PATH)
        values = engine.get_unique_values(column_name)
        return jsonify({"success": True, "values": values})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/filter_raw_data', methods=['POST'])
@login_required
def filter_raw_data():
    try:
        data = request.json
        column_name = data.get('column')
        filter_value = data.get('value')
        
        if not column_name:
            return jsonify({"error": "Missing column name"}), 400
        
        engine = LogicEngine(DB_PATH)
        success = engine.filter_raw_data(column_name, filter_value)
        
        if success:
            return jsonify({"success": True, "message": "Data filtered successfully"})
        else:
            return jsonify({"success": False, "error": "Filtering failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete_template', methods=['POST'])
def delete_template():
    try:
        data = request.json
        profile = data.get('profile', '_TEMPLATES_')
        section = data.get('section')
        name = data.get('name')
        
        if not section or not name:
             return jsonify({"error": "Missing section or name"}), 400
             
        profiles = load_settings()
        
        if profile not in profiles:
            return jsonify({"error": "Profile not found"}), 404
            
        if section not in profiles[profile]:
             return jsonify({"error": "Section not found"}), 404
             
        if name in profiles[profile][section]:
            del profiles[profile][section][name]
            save_settings(profiles)
            return jsonify({"success": True, "message": f"Template '{name}' deleted"})
        else:
            return jsonify({"error": "Template not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')
    
@app.route('/download_file/<path:filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
