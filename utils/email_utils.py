from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

def send_email(to, subject, html_body):
    try:
        msg = Message(subject, recipients=[to], html=html_body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Mail error: {e}")
        return False

def send_registration_pending(user):
    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:600px;margin:auto;background:#f8f9ff;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1a3a6e,#0d6efd);padding:40px 30px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:28px;">🏦 NexusBank</h1>
        <p style="color:#c9d8ff;margin:8px 0 0;">Smart Banking System</p>
      </div>
      <div style="padding:40px 30px;">
        <h2 style="color:#1a3a6e;">Registration Received!</h2>
        <p style="color:#444;line-height:1.7;">Dear <strong>{user.username}</strong>,</p>
        <p style="color:#444;line-height:1.7;">Your registration has been submitted successfully. Our admin team will review your application and get back to you within <strong>24-48 hours</strong>.</p>
        <div style="background:#e8f0fe;border-left:4px solid #0d6efd;padding:15px 20px;border-radius:8px;margin:20px 0;">
          <p style="margin:0;color:#1a3a6e;font-weight:600;">Application Status: <span style="color:#f59e0b;">⏳ Pending Review</span></p>
        </div>
        <p style="color:#888;font-size:13px;margin-top:30px;">NexusBank © 2024 | Smart Banking for Everyone</p>
      </div>
    </div>"""
    send_email(user.email, "NexusBank - Registration Under Review", html)

def send_approval_email(user):
    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:600px;margin:auto;background:#f8f9ff;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1a3a6e,#0d6efd);padding:40px 30px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:28px;">🏦 NexusBank</h1>
      </div>
      <div style="padding:40px 30px;">
        <div style="text-align:center;margin-bottom:20px;">
          <span style="font-size:60px;">✅</span>
        </div>
        <h2 style="color:#1a3a6e;text-align:center;">Account Approved!</h2>
        <p style="color:#444;line-height:1.7;">Dear <strong>{user.username}</strong>,</p>
        <p style="color:#444;line-height:1.7;">Congratulations! Your NexusBank account has been <strong style="color:#16a34a;">approved</strong>. You can now login and access all banking services.</p>
        <div style="text-align:center;margin:30px 0;">
          <a href="#" style="background:linear-gradient(135deg,#1a3a6e,#0d6efd);color:#fff;padding:14px 36px;border-radius:50px;text-decoration:none;font-weight:600;font-size:15px;">Login to NexusBank</a>
        </div>
        <p style="color:#888;font-size:13px;">NexusBank © 2024</p>
      </div>
    </div>"""
    send_email(user.email, "NexusBank - Account Approved! 🎉", html)

def send_rejection_email(user, reason=""):
    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:600px;margin:auto;background:#f8f9ff;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#7f1d1d,#dc2626);padding:40px 30px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:28px;">🏦 NexusBank</h1>
      </div>
      <div style="padding:40px 30px;">
        <h2 style="color:#7f1d1d;">Application Update</h2>
        <p style="color:#444;line-height:1.7;">Dear <strong>{user.username}</strong>,</p>
        <p style="color:#444;line-height:1.7;">After reviewing your application, we regret to inform you that we are unable to approve your account at this time.</p>
        {"<div style='background:#fef2f2;border-left:4px solid #dc2626;padding:15px 20px;border-radius:8px;margin:20px 0;'><p style='margin:0;color:#7f1d1d;'><strong>Reason:</strong> " + reason + "</p></div>" if reason else ""}
        <p style="color:#444;line-height:1.7;">You may contact our support team for further assistance.</p>
        <p style="color:#888;font-size:13px;">NexusBank © 2024</p>
      </div>
    </div>"""
    send_email(user.email, "NexusBank - Application Status Update", html)

def send_appointment_confirmation(user, appointment):
    slot = appointment.slot
    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:600px;margin:auto;background:#f8f9ff;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1a3a6e,#0d6efd);padding:40px 30px;text-align:center;">
        <h1 style="color:#fff;margin:0;">🏦 NexusBank</h1>
      </div>
      <div style="padding:40px 30px;">
        <h2 style="color:#1a3a6e;">Appointment Confirmed!</h2>
        <p>Dear <strong>{user.username}</strong>, your appointment has been booked.</p>
        <div style="background:#e8f0fe;border-radius:12px;padding:20px;margin:20px 0;">
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="color:#666;padding:6px 0;">Service</td><td style="font-weight:600;color:#1a3a6e;">{appointment.service}</td></tr>
            <tr><td style="color:#666;padding:6px 0;">Date</td><td style="font-weight:600;color:#1a3a6e;">{slot.date}</td></tr>
            <tr><td style="color:#666;padding:6px 0;">Time</td><td style="font-weight:600;color:#1a3a6e;">{slot.time}</td></tr>
            <tr><td style="color:#666;padding:6px 0;">Status</td><td><span style="background:#fef9c3;color:#854d0e;padding:3px 10px;border-radius:20px;font-size:13px;">Pending Admin Review</span></td></tr>
          </table>
        </div>
        <p style="color:#888;font-size:13px;">NexusBank © 2024</p>
      </div>
    </div>"""
    send_email(user.email, "NexusBank - Appointment Booked ✅", html)

def send_appointment_update(user, appointment, action, extra=""):
    colors = {'approved': ('#16a34a', '#dcfce7', '✅ Approved'), 'rejected': ('#dc2626', '#fef2f2', '❌ Rejected')}
    c, bg, label = colors.get(action, ('#1a3a6e', '#e8f0fe', 'Updated'))
    slot = appointment.slot
    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:600px;margin:auto;background:#f8f9ff;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1a3a6e,#0d6efd);padding:40px 30px;text-align:center;">
        <h1 style="color:#fff;margin:0;">🏦 NexusBank</h1>
      </div>
      <div style="padding:40px 30px;">
        <h2 style="color:{c};">Appointment {label}</h2>
        <p>Dear <strong>{user.username}</strong>,</p>
        <div style="background:{bg};border-radius:12px;padding:20px;margin:20px 0;">
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="color:#666;padding:6px 0;">Service</td><td style="font-weight:600;">{appointment.service}</td></tr>
            <tr><td style="color:#666;padding:6px 0;">Date</td><td style="font-weight:600;">{slot.date}</td></tr>
            <tr><td style="color:#666;padding:6px 0;">Time</td><td style="font-weight:600;">{slot.time}</td></tr>
            {"<tr><td style='color:#666;padding:6px 0;'>Counter</td><td style='font-weight:600;'>" + (appointment.counter or '') + "</td></tr>" if appointment.counter else ""}
            {"<tr><td style='color:#666;padding:6px 0;'>Assigned Staff</td><td style='font-weight:600;'>" + (appointment.employee.username if appointment.employee else '') + "</td></tr>" if appointment.employee else ""}
          </table>
        </div>
        {("<p style='color:#444;'>" + extra + "</p>") if extra else ""}
        <p style="color:#888;font-size:13px;">NexusBank © 2024</p>
      </div>
    </div>"""
    send_email(user.email, f"NexusBank - Appointment {label}", html)

def send_otp_email(user, otp):
    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:600px;margin:auto;background:#f8f9ff;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1a3a6e,#0d6efd);padding:40px 30px;text-align:center;">
        <h1 style="color:#fff;margin:0;">🏦 NexusBank</h1>
      </div>
      <div style="padding:40px 30px;text-align:center;">
        <h2 style="color:#1a3a6e;">Your Login OTP</h2>
        <p style="color:#444;">Use the code below to complete your login. Valid for 5 minutes.</p>
        <div style="background:linear-gradient(135deg,#1a3a6e,#0d6efd);border-radius:16px;padding:30px;margin:30px auto;display:inline-block;">
          <span style="color:#fff;font-size:40px;font-weight:800;letter-spacing:12px;">{otp}</span>
        </div>
        <p style="color:#dc2626;font-size:13px;">⚠️ Never share this OTP with anyone. NexusBank will never ask for your OTP.</p>
        <p style="color:#888;font-size:13px;">NexusBank © 2024</p>
      </div>
    </div>"""
    send_email(user.email, "NexusBank - Login OTP 🔐", html)

def send_employee_approval(employee):
    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;max-width:600px;margin:auto;background:#f8f9ff;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1a3a6e,#0d6efd);padding:40px 30px;text-align:center;">
        <h1 style="color:#fff;margin:0;">🏦 NexusBank</h1>
      </div>
      <div style="padding:40px 30px;">
        <h2 style="color:#16a34a;">✅ Employee Account Approved</h2>
        <p>Dear <strong>{employee.username}</strong>,</p>
        <p>Your employee account (<strong>{employee.emp_id}</strong>) has been approved. You can now login to your dashboard.</p>
        <p style="color:#888;font-size:13px;">NexusBank © 2024</p>
      </div>
    </div>"""
    send_email(employee.email, "NexusBank - Employee Account Approved", html)
