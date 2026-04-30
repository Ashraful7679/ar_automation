from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from models import db, User
from datetime import datetime, timedelta

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/super-admin')

# Simple hardcoded credentials for Super Admin
SUPER_ADMIN_USER = "superadmin"
SUPER_ADMIN_PASS = "super123"

@super_admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        if user == SUPER_ADMIN_USER and pw == SUPER_ADMIN_PASS:
            session['is_super_admin'] = True
            return redirect(url_for('super_admin.dashboard'))
        return render_template('super_admin/login.html', error="Invalid Credentials")
    return render_template('super_admin/login.html')

@super_admin_bp.route('/dashboard')
def dashboard():
    if not session.get('is_super_admin'):
        return redirect(url_for('super_admin.login'))
    
    admins = User.query.filter_by(is_admin=True).all()
    return render_template('super_admin/dashboard.html', admins=admins, datetime=datetime)

@super_admin_bp.route('/create-admin', methods=['POST'])
def create_admin():
    if not session.get('is_super_admin'):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json if request.is_json else request.form
    username = data.get('username')
    password = data.get('password')
    max_users = int(data.get('max_users', 10))
    expiry_date_str = data.get('expiry_date')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Admin already exists"}), 400
        
    expiry_date = None
    if expiry_date_str:
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")

    new_admin = User(
        username=username, 
        is_admin=True, 
        max_sub_users=max_users,
        expiry_date=expiry_date
    )
    new_admin.set_password(password)
    db.session.add(new_admin)
    db.session.commit()
    
    return jsonify({"success": "Admin created successfully"})

@super_admin_bp.route('/edit-admin', methods=['POST'])
def edit_admin():
    if not session.get('is_super_admin'):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    admin_id = data.get('id')
    admin = User.query.get(admin_id)
    if not admin:
        return jsonify({"error": "Admin not found"}), 404
        
    if data.get('password'):
        admin.set_password(data.get('password'))
    
    if 'max_users' in data:
        admin.max_sub_users = int(data.get('max_users'))
        
    if 'expiry_date' in data:
        admin.expiry_date = datetime.strptime(data.get('expiry_date'), "%Y-%m-%d") if data.get('expiry_date') else None
        
    db.session.commit()
    return jsonify({"success": "Admin updated successfully"})

@super_admin_bp.route('/delete-admin', methods=['POST'])
def delete_admin():
    if not session.get('is_super_admin'):
        return jsonify({"error": "Unauthorized"}), 401
    
    admin_id = request.json.get('id')
    admin = User.query.get(admin_id)
    if admin:
        db.session.delete(admin)
        db.session.commit()
    return jsonify({"success": "Admin deleted successfully"})

@super_admin_bp.route('/logout')
def logout():
    session.pop('is_super_admin', None)
    return redirect(url_for('super_admin.login'))
