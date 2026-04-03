from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json, os
from models import db, User, TimeSlot, Appointment, ChatMessage, Notification
from utils.email_utils import send_appointment_confirmation
from utils.slot_utils import get_available_slots_by_date, get_calendar_data

user_bp = Blueprint('user', __name__, url_prefix='/user')

SERVICES = [
    {'id': 'account_opening', 'name': 'Account Opening', 'icon': 'bi-bank', 'color': '#0d6efd', 'desc': 'Open savings, current or FD accounts'},
    {'id': 'loan_enquiry', 'name': 'Loan Enquiry', 'icon': 'bi-cash-coin', 'color': '#16a34a', 'desc': 'Personal, home, car or business loans'},
    {'id': 'document_submission', 'name': 'Document Submission', 'icon': 'bi-file-earmark-text', 'color': '#f59e0b', 'desc': 'Submit KYC and verification documents'},
    {'id': 'credit_card', 'name': 'Credit Card', 'icon': 'bi-credit-card', 'color': '#8b5cf6', 'desc': 'Apply for credit or debit cards'},
    {'id': 'internet_banking', 'name': 'Internet Banking', 'icon': 'bi-globe', 'color': '#06b6d4', 'desc': 'Setup online banking access'},
    {'id': 'fixed_deposit', 'name': 'Fixed Deposit', 'icon': 'bi-safe', 'color': '#ec4899', 'desc': 'Open or renew fixed deposits'},
    {'id': 'insurance', 'name': 'Insurance', 'icon': 'bi-shield-check', 'color': '#10b981', 'desc': 'Life, health and property insurance'},
    {'id': 'grievance', 'name': 'Grievance / Complaint', 'icon': 'bi-headset', 'color': '#f97316', 'desc': 'Report issues or file complaints'},
]

def require_user():
    if not isinstance(current_user._get_current_object(), User):
        return redirect(url_for('auth.login'))
    return None


@user_bp.route('/dashboard')
@login_required
def dashboard():
    r = require_user()
    if r: return r
    appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.created_at.desc()).limit(5).all()
    pending = Appointment.query.filter_by(user_id=current_user.id, status='pending').count()
    approved = Appointment.query.filter_by(user_id=current_user.id, status='approved').count()
    completed = Appointment.query.filter_by(user_id=current_user.id, status='completed').count()
    notifications = Notification.query.filter_by(recipient_id=current_user.id, recipient_type='user', is_read=False).order_by(Notification.created_at.desc()).limit(10).all()
    return render_template('user/dashboard.html', appointments=appointments,
                           pending=pending, approved=approved, completed=completed,
                           notifications=notifications, services=SERVICES)


@user_bp.route('/book-appointment', methods=['GET'])
@login_required
def book_appointment():
    r = require_user()
    if r: return r
    # Check if user already has active booking
    active = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.status.in_(['pending', 'approved'])
    ).first()
    now = datetime.now()
    return render_template('user/book_appointment.html', services=SERVICES,
                           current_month=now.month, current_year=now.year,
                           has_active_booking=active)


@user_bp.route('/api/calendar-slots')
@login_required
def api_calendar_slots():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    data = get_calendar_data(month, year)
    return jsonify(data)


@user_bp.route('/api/slots/<date>')
@login_required
def api_slots_for_date(date):
    slots = get_available_slots_by_date(date)
    result = []
    for s in slots:
        # Check if current user already booked this slot
        user_booked = Appointment.query.filter_by(
            user_id=current_user.id, slot_id=s.id,
        ).filter(Appointment.status.notin_(['cancelled'])).first()
        result.append({
            'id': s.id, 'time': s.time,
            'available': s.is_available,
            'seats_left': s.seats_left,
            'max': s.max_capacity,
            'booked': s.booked_count,
            'user_booked': bool(user_booked)
        })
    return jsonify(result)


@user_bp.route('/api/book', methods=['POST'])
@login_required
def api_book():
    r = require_user()
    if r: return jsonify({'success': False, 'message': 'Unauthorized'})

    data = request.get_json()
    slot_id = data.get('slot_id')
    service = data.get('service')

    if not slot_id or not service:
        return jsonify({'success': False, 'message': 'Missing data'})

    # Check user doesn't have active booking
    active = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.status.in_(['pending', 'approved'])
    ).first()
    if active:
        return jsonify({'success': False, 'message': 'You already have an active appointment. Cancel or reschedule it first.'})

    slot = TimeSlot.query.get(slot_id)
    if not slot or not slot.is_available:
        return jsonify({'success': False, 'message': 'Slot no longer available'})

    apt = Appointment(user_id=current_user.id, slot_id=slot_id, service=service, status='pending')
    slot.booked_count += 1
    db.session.add(apt)
    db.session.commit()

    send_appointment_confirmation(current_user, apt)
    _notify_user(current_user.id, f"Your appointment for {service} on {slot.date} at {slot.time} has been booked.")
    return jsonify({'success': True, 'message': 'Appointment booked successfully!', 'appointment_id': apt.id})


@user_bp.route('/api/reschedule', methods=['POST'])
@login_required
def api_reschedule():
    data = request.get_json()
    apt_id = data.get('appointment_id')
    new_slot_id = data.get('new_slot_id')

    apt = Appointment.query.filter_by(id=apt_id, user_id=current_user.id).first()
    if not apt:
        return jsonify({'success': False, 'message': 'Appointment not found'})
    if apt.status not in ['pending']:
        return jsonify({'success': False, 'message': 'Cannot reschedule this appointment'})

    new_slot = TimeSlot.query.get(new_slot_id)
    if not new_slot or not new_slot.is_available:
        return jsonify({'success': False, 'message': 'Selected slot not available'})

    # Release old slot
    old_slot = TimeSlot.query.get(apt.slot_id)
    if old_slot and old_slot.booked_count > 0:
        old_slot.booked_count -= 1

    apt.slot_id = new_slot_id
    new_slot.booked_count += 1
    apt.status = 'pending'
    apt.employee_id = None
    apt.counter = None
    db.session.commit()

    _notify_user(current_user.id, f"Appointment rescheduled to {new_slot.date} at {new_slot.time}")
    return jsonify({'success': True, 'message': 'Appointment rescheduled!'})


@user_bp.route('/api/cancel', methods=['POST'])
@login_required
def api_cancel():
    data = request.get_json()
    apt_id = data.get('appointment_id')

    apt = Appointment.query.filter_by(id=apt_id, user_id=current_user.id).first()
    if not apt:
        return jsonify({'success': False, 'message': 'Not found'})
    if apt.status == 'completed':
        return jsonify({'success': False, 'message': 'Cannot cancel completed appointment'})

    old_slot = TimeSlot.query.get(apt.slot_id)
    if old_slot and old_slot.booked_count > 0:
        old_slot.booked_count -= 1

    apt.status = 'cancelled'
    db.session.commit()
    _notify_user(current_user.id, "Your appointment has been cancelled.")
    return jsonify({'success': True, 'message': 'Appointment cancelled'})


@user_bp.route('/my-appointments')
@login_required
def my_appointments():
    r = require_user()
    if r: return r
    appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.created_at.desc()).all()
    return render_template('user/my_appointments.html', appointments=appointments, services=SERVICES)


@user_bp.route('/chat/<int:apt_id>')
@login_required
def chat(apt_id):
    r = require_user()
    if r: return r
    apt = Appointment.query.filter_by(id=apt_id, user_id=current_user.id).first_or_404()
    if apt.status not in ['approved'] or not apt.employee_id:
        flash('Chat is only available after your appointment is approved and staff is assigned.', 'warning')
        return redirect(url_for('user.my_appointments'))
    messages = ChatMessage.query.filter_by(appointment_id=apt_id).order_by(ChatMessage.timestamp.asc()).all()
    # Mark messages as read
    ChatMessage.query.filter_by(appointment_id=apt_id, sender_type='employee', is_read=False).update({'is_read': True})
    db.session.commit()
    return render_template('user/chat.html', appointment=apt, messages=messages)


@user_bp.route('/api/chat/send', methods=['POST'])
@login_required
def api_chat_send():
    data = request.form
    apt_id = int(data.get('appointment_id'))
    message_text = data.get('message', '')

    apt = Appointment.query.filter_by(id=apt_id, user_id=current_user.id).first()
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
        return jsonify({'success': False, 'message': 'Empty message'})

    msg = ChatMessage(
        appointment_id=apt_id, sender_id=current_user.id,
        sender_type='user', message=message_text,
        file_url=file_url, file_type=file_type
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({'success': True, 'message_id': msg.id, 'timestamp': msg.timestamp.strftime('%H:%M')})


@user_bp.route('/api/chat/messages/<int:apt_id>')
@login_required
def api_chat_messages(apt_id):
    apt = Appointment.query.filter_by(id=apt_id, user_id=current_user.id).first()
    if not apt:
        return jsonify([])
    since = request.args.get('since', 0, type=int)
    msgs = ChatMessage.query.filter(ChatMessage.appointment_id == apt_id, ChatMessage.id > since).order_by(ChatMessage.timestamp.asc()).all()
    ChatMessage.query.filter_by(appointment_id=apt_id, sender_type='employee', is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify([{
        'id': m.id, 'sender_type': m.sender_type, 'message': m.message,
        'file_url': m.file_url, 'file_type': m.file_type,
        'timestamp': m.timestamp.strftime('%I:%M %p'),
        'sender_name': current_user.username if m.sender_type == 'user' else (apt.employee.username if apt.employee else 'Staff')
    } for m in msgs])


@user_bp.route('/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(recipient_id=current_user.id, recipient_type='user').update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@user_bp.route('/profile')
@login_required
def profile():
    r = require_user()
    if r: return r
    return render_template('user/profile.html')


def _notify_user(user_id, message):
    n = Notification(recipient_id=user_id, recipient_type='user', message=message)
    db.session.add(n)
    db.session.commit()
