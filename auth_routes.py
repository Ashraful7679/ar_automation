from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, FileHistory
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Check for subscription expiry
            if user.expiry_date and datetime.now() > user.expiry_date:
                flash(f'Account expired on {user.expiry_date.strftime("%Y-%m-%d")}. Please contact administrator.')
                return render_template('login.html')

            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('index'))
        
    # Admins see ONLY users created by themselves
    users = User.query.filter_by(created_by_id=current_user.id).all()
    
    return render_template('admin_dashboard.html', users=users, datetime=datetime)

@auth_bp.route('/admin/add_user', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    # Check max sub-users limit
    if current_user.max_sub_users != -1:
        current_sub_users = User.query.filter_by(created_by_id=current_user.id).count()
        if current_sub_users >= current_user.max_sub_users:
            return jsonify({"error": f"You have reached your limit of {current_user.max_sub_users} users."}), 403

    data = request.json
    username = data.get('username')
    password = data.get('password')
    expiry_date_str = data.get('expiry_date')
    total_quota = int(data.get('total_quota', 1000))
    daily_quota = int(data.get('daily_quota', 50))
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400
        
    expiry_date = None
    if expiry_date_str:
        try:
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
    
    new_user = User(
        username=username, 
        is_admin=False, 
        expiry_date=expiry_date,
        created_by_id=current_user.id,
        total_quota=total_quota,
        daily_quota=daily_quota
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"success": True})

@auth_bp.route('/admin/edit_user', methods=['POST'])
@login_required
def edit_user():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    user = User.query.get(data.get('id'))
    if not user or (user.created_by_id != current_user.id and user.id != current_user.id):
        return jsonify({"error": "User not found or access denied"}), 404
        
    if data.get('password'):
        user.set_password(data.get('password'))
    
    if 'total_quota' in data:
        user.total_quota = int(data.get('total_quota'))
    if 'daily_quota' in data:
        user.daily_quota = int(data.get('daily_quota'))
    if 'expiry_date' in data:
        user.expiry_date = datetime.strptime(data.get('expiry_date'), "%Y-%m-%d") if data.get('expiry_date') else None
        
    db.session.commit()
    return jsonify({"success": True})

@auth_bp.route('/admin/delete_user', methods=['POST'])
@login_required
def delete_user():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    user_id = request.json.get('id')
    user = User.query.get(user_id)
    if user and user.created_by_id == current_user.id:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Unauthorized or not found"}), 403
