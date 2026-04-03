from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
from models import db, Employee, Appointment, ChatMessage, User, Notification

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

def require_employee():
    if not isinstance(current_user._get_current_object(), Employee):
        return redirect(url_for('auth.employee_login'))
    return None


@employee_bp.route('/dashboard')
@login_required
def dashboard():
    r = require_employee()
    if r: return r

    assigned = Appointment.query.filter(
        Appointment.employee_id == current_user.id,
        Appointment.status.in_(['approved'])
    ).all()

    completed = Appointment.query.filter_by(
        employee_id=current_user.id, status='completed'
    ).order_by(Appointment.updated_at.desc()).limit(10).all()

    pending_count = len(assigned)
    completed_count = Appointment.query.filter_by(employee_id=current_user.id, status='completed').count()
    total_count = Appointment.query.filter_by(employee_id=current_user.id).count()

    # Unread messages count per appointment
    unread = {}
    for apt in assigned:
        count = ChatMessage.query.filter_by(
            appointment_id=apt.id, sender_type='user', is_read=False
        ).count()
        unread[apt.id] = count

    return render_template('employee/dashboard.html',
                           assigned=assigned, completed=completed,
                           pending_count=pending_count, completed_count=completed_count,
                           total_count=total_count, unread=unread)


@employee_bp.route('/customer/<int:apt_id>')
@login_required
def customer_detail(apt_id):
    r = require_employee()
    if r: return r
    apt = Appointment.query.filter_by(id=apt_id, employee_id=current_user.id).first_or_404()
    return render_template('employee/customer_detail.html', appointment=apt, user=apt.user)


@employee_bp.route('/chat/<int:apt_id>')
@login_required
def chat(apt_id):
    r = require_employee()
    if r: return r
    apt = Appointment.query.filter_by(id=apt_id, employee_id=current_user.id).first_or_404()
    messages = ChatMessage.query.filter_by(appointment_id=apt_id).order_by(ChatMessage.timestamp.asc()).all()
    # Mark user messages as read
    ChatMessage.query.filter_by(appointment_id=apt_id, sender_type='user', is_read=False).update({'is_read': True})
    db.session.commit()
    return render_template('employee/chat.html', appointment=apt, messages=messages)


@employee_bp.route('/api/chat/send', methods=['POST'])
@login_required
def api_chat_send():
    data = request.form
    apt_id = int(data.get('appointment_id'))
    message_text = data.get('message', '')

    apt = Appointment.query.filter_by(id=apt_id, employee_id=current_user.id).first()
    if not apt:
        return jsonify({'success': False})

    file_url = None
    file_type = None
    if 'file' in request.files:
        f = request.files['file']
        if f and f.filename:
            chat_dir = os.path.join('static', 'uploads', 'chat')
            os.makedirs(chat_dir, exist_ok=True)
            filename = f"chat_{apt_id}_{int(datetime.now().timestamp())}_{f.filename}"
            filepath = os.path.join(chat_dir, filename)
            f.save(filepath)
            file_url = f"/static/uploads/chat/{filename}"
            ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
            file_type = 'image' if ext in ['png','jpg','jpeg','gif','webp'] else 'doc'

    if not message_text and not file_url:
        return jsonify({'success': False})

    msg = ChatMessage(
        appointment_id=apt_id, sender_id=current_user.id,
        sender_type='employee', message=message_text,
        file_url=file_url, file_type=file_type
    )
    db.session.add(msg)

    # Notify user
    n = Notification(recipient_id=apt.user_id, recipient_type='user',
                     message=f"New message from your assigned staff {current_user.username}")
    db.session.add(n)
    db.session.commit()

    return jsonify({'success': True, 'message_id': msg.id, 'timestamp': msg.timestamp.strftime('%H:%M')})


@employee_bp.route('/api/chat/messages/<int:apt_id>')
@login_required
def api_chat_messages(apt_id):
    apt = Appointment.query.filter_by(id=apt_id, employee_id=current_user.id).first()
    if not apt:
        return jsonify([])
    since = request.args.get('since', 0, type=int)
    msgs = ChatMessage.query.filter(
        ChatMessage.appointment_id == apt_id, ChatMessage.id > since
    ).order_by(ChatMessage.timestamp.asc()).all()
    ChatMessage.query.filter_by(appointment_id=apt_id, sender_type='user', is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify([{
        'id': m.id, 'sender_type': m.sender_type, 'message': m.message,
        'file_url': m.file_url, 'file_type': m.file_type,
        'timestamp': m.timestamp.strftime('%I:%M %p'),
        'sender_name': apt.user.username if m.sender_type == 'user' else current_user.username
    } for m in msgs])


@employee_bp.route('/api/complete/<int:apt_id>', methods=['POST'])
@login_required
def complete_appointment(apt_id):
    r = require_employee()
    if r: return jsonify({'success': False})
    apt = Appointment.query.filter_by(id=apt_id, employee_id=current_user.id).first()
    if not apt:
        return jsonify({'success': False, 'message': 'Not found'})
    apt.status = 'completed'
    apt.updated_at = datetime.utcnow()
    db.session.commit()
    n = Notification(recipient_id=apt.user_id, recipient_type='user',
                     message=f"Your appointment for {apt.service} has been marked as completed.")
    db.session.add(n)
    db.session.commit()
    return jsonify({'success': True})
