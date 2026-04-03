from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import db, User, Employee, Admin, TimeSlot, Appointment, ChatMessage, Notification
from utils.email_utils import (send_approval_email, send_rejection_email,
                                send_appointment_update, send_employee_approval)
from utils.slot_utils import DEFAULT_SLOT_TIMES

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_admin():
    if not isinstance(current_user._get_current_object(), Admin):
        return redirect(url_for('auth.admin_login'))
    return None


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    r = require_admin()
    if r: return r

    stats = {
        'total_users': User.query.count(),
        'pending_users': User.query.filter_by(status='pending').count(),
        'approved_users': User.query.filter_by(status='approved').count(),
        'total_employees': Employee.query.count(),
        'pending_employees': Employee.query.filter_by(status='pending').count(),
        'total_appointments': Appointment.query.count(),
        'pending_appointments': Appointment.query.filter_by(status='pending').count(),
        'approved_appointments': Appointment.query.filter_by(status='approved').count(),
        'completed_appointments': Appointment.query.filter_by(status='completed').count(),
    }

    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # Analytics by service
    from sqlalchemy import func
    service_counts = db.session.query(
        Appointment.service, func.count(Appointment.id)
    ).group_by(Appointment.service).all()

    return render_template('admin/dashboard.html', stats=stats,
                           recent_appointments=recent_appointments,
                           recent_users=recent_users,
                           service_counts=service_counts)


# ── USERS ──────────────────────────────────────────────────────
@admin_bp.route('/users')
@login_required
def users():
    r = require_admin()
    if r: return r
    status_filter = request.args.get('status', '')
    q = request.args.get('q', '')
    query = User.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if q:
        query = query.filter(
            (User.username.ilike(f'%{q}%')) | (User.email.ilike(f'%{q}%'))
        )
    users_list = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users_list, status_filter=status_filter, q=q)


@admin_bp.route('/users/<int:user_id>')
@login_required
def user_detail(user_id):
    r = require_admin()
    if r: return r
    user = User.query.get_or_404(user_id)
    appointments = Appointment.query.filter_by(user_id=user_id).all()
    return render_template('admin/user_detail.html', user=user, appointments=appointments)


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
def approve_user(user_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    user = User.query.get_or_404(user_id)
    user.status = 'approved'
    db.session.commit()
    send_approval_email(user)
    _notify_user(user.id, "Your NexusBank account has been approved! You can now login.")
    return jsonify({'success': True, 'message': f'{user.username} approved'})


@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@login_required
def reject_user(user_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    data = request.get_json()
    reason = data.get('reason', '')
    user = User.query.get_or_404(user_id)
    user.status = 'rejected'
    db.session.commit()
    send_rejection_email(user, reason)
    return jsonify({'success': True})


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})


# ── EMPLOYEES ──────────────────────────────────────────────────
@admin_bp.route('/employees')
@login_required
def employees():
    r = require_admin()
    if r: return r
    status_filter = request.args.get('status', '')
    query = Employee.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    emps = query.order_by(Employee.created_at.desc()).all()
    # For each emp, count assignments
    emp_data = []
    for emp in emps:
        total = Appointment.query.filter_by(employee_id=emp.id).count()
        completed = Appointment.query.filter_by(employee_id=emp.id, status='completed').count()
        active = Appointment.query.filter(Appointment.employee_id==emp.id, Appointment.status.in_(['approved'])).count()
        emp_data.append({'emp': emp, 'total': total, 'completed': completed, 'active': active})
    return render_template('admin/employees.html', emp_data=emp_data, status_filter=status_filter)


@admin_bp.route('/employees/<int:emp_id>/approve', methods=['POST'])
@login_required
def approve_employee(emp_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    emp = Employee.query.get_or_404(emp_id)
    emp.status = 'approved'
    db.session.commit()
    send_employee_approval(emp)
    return jsonify({'success': True})


@admin_bp.route('/employees/<int:emp_id>/delete', methods=['POST'])
@login_required
def delete_employee(emp_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    emp = Employee.query.get_or_404(emp_id)
    db.session.delete(emp)
    db.session.commit()
    return jsonify({'success': True})


# ── APPOINTMENTS ───────────────────────────────────────────────
@admin_bp.route('/appointments')
@login_required
def appointments():
    r = require_admin()
    if r: return r
    status_filter = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    query = Appointment.query.join(TimeSlot)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    if date_filter:
        query = query.filter(TimeSlot.date == date_filter)
    apts = query.order_by(Appointment.created_at.desc()).all()
    employees = Employee.query.filter_by(status='approved').all()

    # Group employee load
    emp_load = {}
    for emp in employees:
        active_count = Appointment.query.filter(
            Appointment.employee_id == emp.id,
            Appointment.status == 'approved'
        ).count()
        emp_load[emp.id] = active_count

    return render_template('admin/appointments.html', appointments=apts,
                           employees=employees, emp_load=emp_load,
                           status_filter=status_filter, date_filter=date_filter)


@admin_bp.route('/appointments/<int:apt_id>/allocate', methods=['POST'])
@login_required
def allocate_appointment(apt_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    data = request.get_json()
    emp_id = data.get('employee_id')
    counter = data.get('counter', '')

    apt = Appointment.query.get_or_404(apt_id)

    if emp_id:
        emp = Employee.query.get(emp_id)
        # Check emp limit (max 2 active)
        active_count = Appointment.query.filter(
            Appointment.employee_id == emp_id,
            Appointment.status == 'approved'
        ).count()
        if active_count >= 2:
            return jsonify({'success': False, 'message': f'{emp.username} is at full capacity (2 customers)'})

    apt.employee_id = emp_id if emp_id else None
    apt.counter = counter
    apt.status = 'approved'
    db.session.commit()

    send_appointment_update(apt.user, apt, 'approved')
    _notify_user(apt.user_id, f"Your appointment has been approved! Counter: {counter}, Staff: {apt.employee.username if apt.employee else 'TBA'}")
    return jsonify({'success': True, 'message': 'Appointment allocated'})


@admin_bp.route('/appointments/<int:apt_id>/reject', methods=['POST'])
@login_required
def reject_appointment(apt_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    data = request.get_json()
    reason = data.get('reason', '')
    apt = Appointment.query.get_or_404(apt_id)
    apt.status = 'rejected'
    apt.admin_notes = reason

    slot = TimeSlot.query.get(apt.slot_id)
    if slot and slot.booked_count > 0:
        slot.booked_count -= 1
    db.session.commit()

    send_appointment_update(apt.user, apt, 'rejected', reason)
    _notify_user(apt.user_id, f"Your appointment has been rejected. Reason: {reason}")
    return jsonify({'success': True})


# ── SLOTS MANAGEMENT ──────────────────────────────────────────
@admin_bp.route('/slots')
@login_required
def slots():
    r = require_admin()
    if r: return r
    date_filter = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    slots_list = TimeSlot.query.filter_by(date=date_filter).order_by(TimeSlot.time).all()
    return render_template('admin/slots.html', slots=slots_list,
                           date_filter=date_filter, default_times=DEFAULT_SLOT_TIMES)


@admin_bp.route('/slots/add', methods=['POST'])
@login_required
def add_slot():
    r = require_admin()
    if r: return jsonify({'success': False})
    data = request.get_json()
    date = data.get('date')
    times = data.get('times', [])
    capacity = int(data.get('capacity', 2))

    added = 0
    for t in times:
        existing = TimeSlot.query.filter_by(date=date, time=t).first()
        if not existing:
            slot = TimeSlot(date=date, time=t, max_capacity=capacity)
            db.session.add(slot)
            added += 1
    db.session.commit()
    return jsonify({'success': True, 'added': added})


@admin_bp.route('/slots/<int:slot_id>/toggle', methods=['POST'])
@login_required
def toggle_slot(slot_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    slot = TimeSlot.query.get_or_404(slot_id)
    slot.is_active = not slot.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': slot.is_active})


@admin_bp.route('/slots/<int:slot_id>/delete', methods=['POST'])
@login_required
def delete_slot(slot_id):
    r = require_admin()
    if r: return jsonify({'success': False})
    slot = TimeSlot.query.get_or_404(slot_id)
    if slot.booked_count > 0:
        return jsonify({'success': False, 'message': 'Cannot delete slot with bookings'})
    db.session.delete(slot)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/analytics')
@login_required
def api_analytics():
    from sqlalchemy import func
    # Service distribution
    service_data = db.session.query(
        Appointment.service, func.count(Appointment.id)
    ).group_by(Appointment.service).all()

    # Status distribution
    status_data = db.session.query(
        Appointment.status, func.count(Appointment.id)
    ).group_by(Appointment.status).all()

    # Daily bookings last 7 days
    from datetime import timedelta
    daily = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        count = db.session.query(func.count(Appointment.id)).join(TimeSlot).filter(TimeSlot.date == day).scalar()
        daily.append({'date': day, 'count': count or 0})

    return jsonify({
        'services': [{'name': s, 'count': c} for s, c in service_data],
        'statuses': [{'status': s, 'count': c} for s, c in status_data],
        'daily': daily
    })


def _notify_user(user_id, message):
    n = Notification(recipient_id=user_id, recipient_type='user', message=message)
    db.session.add(n)
    db.session.commit()
