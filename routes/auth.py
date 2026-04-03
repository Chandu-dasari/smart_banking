from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import random, json, os
from models import db, User, Employee, Admin
from utils.email_utils import send_registration_pending, send_otp_email
from utils.face_utils import encode_face_from_image, verify_face, base64_to_bytes, detect_faces_in_frame

auth_bp = Blueprint('auth', __name__)

# ── USER REGISTER ──────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        if User.query.filter_by(email=data['email']).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(username=data['username']).first():
            flash('Username taken.', 'error')
            return redirect(url_for('auth.register'))

        user = User(
            username=data['username'], email=data['email'],
            contact=data.get('contact',''), address=data.get('address',''),
            dob=data.get('dob',''), id_type=data.get('id_type',''),
            id_number=data.get('id_number',''), occupation=data.get('occupation',''),
            status='pending'
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        session['pending_face_user_id'] = user.id
        return redirect(url_for('auth.face_register'))
    return render_template('auth/register.html')


@auth_bp.route('/face-register', methods=['GET', 'POST'])
def face_register():
    user_id = session.get('pending_face_user_id')
    if not user_id:
        return redirect(url_for('auth.register'))
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        data = request.get_json()
        img_b64 = data.get('image')
        if not img_b64:
            return jsonify({'success': False, 'message': 'No image data'})

        img_bytes = base64_to_bytes(img_b64)
        encoding = encode_face_from_image(img_bytes)

        if encoding is None:
            return jsonify({'success': False, 'message': 'No face detected. Please ensure your face is clearly visible.'})

        # Save face image
        face_dir = os.path.join('static', 'uploads', 'faces')
        os.makedirs(face_dir, exist_ok=True)
        face_filename = f"face_{user.id}.jpg"
        face_path = os.path.join(face_dir, face_filename)
        with open(face_path, 'wb') as f:
            f.write(img_bytes)

        # Save to known_faces folder
        known_dir = 'known_faces'
        os.makedirs(known_dir, exist_ok=True)
        with open(os.path.join(known_dir, f"{user.username}.jpg"), 'wb') as f:
            f.write(img_bytes)

        user.face_image = face_filename
        user.face_encoding = json.dumps(encoding)
        db.session.commit()

        send_registration_pending(user)
        session.pop('pending_face_user_id', None)
        return jsonify({'success': True, 'message': 'Face registered! Redirecting...',
                        'redirect': url_for('auth.login')})

    return render_template('auth/face_register.html', user=user)


@auth_bp.route('/detect-face', methods=['POST'])
def detect_face():
    data = request.get_json()
    img_b64 = data.get('image')
    if not img_b64:
        return jsonify({'faces': []})
    img_bytes = base64_to_bytes(img_b64)
    faces = detect_faces_in_frame(img_bytes)
    return jsonify({'faces': faces})


# ── USER LOGIN ─────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid credentials.', 'error')
            return redirect(url_for('auth.login'))

        if user.status == 'pending':
            flash('Your account is pending admin approval.', 'warning')
            return redirect(url_for('auth.login'))
        if user.status == 'rejected':
            flash('Your account has been rejected. Contact support.', 'error')
            return redirect(url_for('auth.login'))

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        user.otp_secret = otp
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()

        send_otp_email(user, otp)
        session['otp_user_id'] = user.id
        return redirect(url_for('auth.verify_otp'))

    return render_template('auth/login.html')


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    user_id = session.get('otp_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)

    if request.method == 'POST':
        otp_entered = request.form.get('otp')
        if not user.otp_secret or not user.otp_expiry:
            flash('OTP expired. Try again.', 'error')
            return redirect(url_for('auth.login'))
        if datetime.utcnow() > user.otp_expiry:
            flash('OTP expired. Try again.', 'error')
            return redirect(url_for('auth.login'))
        if otp_entered != user.otp_secret:
            flash('Invalid OTP.', 'error')
            return redirect(url_for('auth.verify_otp'))

        user.otp_secret = None
        user.otp_expiry = None
        db.session.commit()
        session['face_verify_user_id'] = user.id
        session.pop('otp_user_id', None)
        return redirect(url_for('auth.face_verify'))

    return render_template('auth/verify_otp.html')


@auth_bp.route('/face-verify', methods=['GET', 'POST'])
def face_verify():
    user_id = session.get('face_verify_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)

    if request.method == 'POST':
        data = request.get_json()
        img_b64 = data.get('image')
        if not img_b64:
            return jsonify({'success': False, 'message': 'No image received'})

        img_bytes = base64_to_bytes(img_b64)
        if not user.face_encoding:
            # No face enrolled, allow login
            match, score = True, 1.0
        else:
            match, score = verify_face(img_bytes, user.face_encoding)

        if match:
            session.pop('face_verify_user_id', None)
            login_user(user)
            return jsonify({'success': True, 'score': score,
                            'redirect': url_for('user.dashboard')})
        else:
            return jsonify({'success': False, 'score': score,
                            'message': f'Face not recognized (similarity: {score:.2f}). Try again.'})

    return render_template('auth/face_verify.html', user=user)


# ── EMPLOYEE LOGIN ─────────────────────────────────────────────
@auth_bp.route('/employee/register', methods=['GET', 'POST'])
def employee_register():
    if request.method == 'POST':
        data = request.form
        if Employee.query.filter_by(emp_id=data['emp_id']).first():
            flash('Employee ID already registered.', 'error')
            return redirect(url_for('auth.employee_register'))
        emp = Employee(
            emp_id=data['emp_id'], username=data['username'],
            email=data['email'], department=data.get('department',''),
            contact=data.get('contact',''), status='pending'
        )
        emp.set_password(data['password'])
        db.session.add(emp)
        db.session.commit()
        flash('Registration submitted. Awaiting admin approval.', 'success')
        return redirect(url_for('auth.employee_login'))
    return render_template('auth/employee_register.html')


@auth_bp.route('/employee/login', methods=['GET', 'POST'])
def employee_login():
    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        password = request.form.get('password')
        emp = Employee.query.filter_by(emp_id=emp_id).first()

        if not emp or not emp.check_password(password):
            flash('Invalid credentials.', 'error')
            return redirect(url_for('auth.employee_login'))
        if emp.status != 'approved':
            flash('Account pending admin approval.', 'warning')
            return redirect(url_for('auth.employee_login'))

        login_user(emp)
        return redirect(url_for('employee.dashboard'))

    return render_template('auth/employee_login.html')


# ── ADMIN LOGIN ────────────────────────────────────────────────
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if not admin or not admin.check_password(password):
            flash('Invalid credentials.', 'error')
            return redirect(url_for('auth.admin_login'))
        login_user(admin)
        return redirect(url_for('admin.dashboard'))
    return render_template('auth/admin_login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@auth_bp.route('/resend-otp')
def resend_otp():
    user_id = session.get('otp_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)
    otp = str(random.randint(100000, 999999))
    user.otp_secret = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    db.session.commit()
    send_otp_email(user, otp)
    flash('OTP resent to your email.', 'success')
    return redirect(url_for('auth.verify_otp'))
