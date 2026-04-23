from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import shutil
import pandas as pd
from logic_engine import LogicEngine
import traceback
import sys
from flask_login import LoginManager, login_required, current_user
from models import db, User, FileHistory
from auth_routes import auth_bp

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

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

if os.environ.get('RENDER') or getattr(sys, 'frozen', False):
    UPLOAD_FOLDER = '/tmp/uploads'
    OUTPUT_FOLDER = '/tmp/output'
    OUTPUT_FOLDER_STATIC = os.path.join(OUTPUT_FOLDER)
else:
    OUTPUT_FOLDER_STATIC = os.path.join(RESOURCE_DIR, 'static', 'output')

if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
        }
    }
    DB_PATH = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'ar_system.db') + '?timeout=30'
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
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp)

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
        
        # Generate unique filename to avoid permission errors on locked files
        filename = file.filename
        name, ext = os.path.splitext(filename)
        import time
        unique_filename = f"{name}_{int(time.time())}{ext}"
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
        
        # Generate unique filename to avoid permission errors on locked files
        filename = file.filename
        name, ext = os.path.splitext(filename)
        import time
        unique_filename = f"{name}_{int(time.time())}{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        # Note: logic_engine now handles table clearing, so we don't need to delete the file
        # which prevents WinError 32
        
        profile = request.form.get('profile', 'default')
        sheet_name = request.form.get('sheet', None)  # Get selected sheet
        
        engine = LogicEngine(DB_PATH)
        engine.load_file(filepath, profile_name=profile, sheet_name=sheet_name)
        
        # Get both previews
        raw_preview = engine.get_preview()
        formatted_preview = engine.get_formatted_preview()
        engine.close()
        
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

def save_history(input_file, output_file):
    try:
        if not input_file or not output_file: return
        
        # Save to DB
        hist = FileHistory(input_filename=input_file, output_filename=output_file)
        db.session.add(hist)
        db.session.commit()
        
        # Prune > 10
        count = FileHistory.query.count()
        if count > 10:
            oldest = FileHistory.query.order_by(FileHistory.created_at.asc()).first()
            if oldest:
                db.session.delete(oldest)
                db.session.commit()
                # Determine if we should delete file from disk? 
                # User said "system should save the last 10 input files". 
                # So we should delete older ones to save space?
                # For now, let's just track in DB. Logic to delete actual files is complex (shared inputs?)
                pass
    except Exception as e:
        print(f"History Save Error: {e}")

@app.route('/api/run', methods=['POST'])
@login_required
def run_process():
    try:
        data = request.json
        profile = data.get('profile', {})
        
        engine = LogicEngine(DB_PATH)
        files = engine.generate_outputs(OUTPUT_FOLDER)
        
        # Determine Input File (hacky, as LogicEngine might have changed)
        # We can pass input filename from frontend or store in session?
        # LogicEngine doesn't track filename implicitly unless we modified it.
        # But `get_sheets` saves to uploads.
        # Let's assume the last uploaded file.
        # Ideally, frontend sends `input_filename`.
        
        input_filename = "Input_File.xlsx" # Placeholder or need to fetch
        if files:
            save_history(input_filename, files[0])
            
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
        custom_filename = data.get('filename') # Support Custom Filename
        file_format = data.get('format', 'xlsx')
        
        engine = LogicEngine(DB_PATH)
        filename = engine.generate_custom_output(profile, custom_filename, file_format)
        engine.close()
        
        # Save history for direct export too?
        # Maybe? User said "last 10 input files... along with output".
        # If export is the main action, capture it.
        save_history("Uploaded_File.xlsx", filename)
        
        return jsonify({'message': 'Export generated', 'file': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        # Backend Index Adjustment handled in JS or LogicEngine?
        # LogicEngine.update_formatted_cell expects index into formatted_headers.
        # Frontend sends Visible Index (0 based).
        # Frontend rowData = row.slice(1). Row[0] is _id.
        # So Frontend Index 0 maps to Row Index 1.
        # Row Index 1 corresponds to formatted_headers[0].
        # LogicEngine expects index into formatted_headers.
        # So Frontend Index 0 -> logic_engine index 0.
        # Therefore, we use int(col_index) directly.
        
        success = engine.update_formatted_cell(row_id, int(col_index), new_value)
        engine.close()
        
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_data_batch', methods=['POST'])
def update_data_batch():
    try:
        data = request.json
        updates = data.get('updates') # list of {row_id, col_index, value}
        
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
        row_ids = data.get('row_ids') # List of IDs
        
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
        print(f"DEBUG: get_settings for {profile}, section {section}")
        
        if section:
            settings = settings.get(section, {})
        
        print(f"DEBUG: Returning {len(settings)} items")
            
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        print(f"DEBUG: get_settings Error: {e}")
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
        section = data.get('section') # 'mapping' or 'rules'
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
