import os
from flask import Flask
from flask_login import LoginManager
from config import Config
from models import db, User, Employee, Admin
from utils.email_utils import mail
from utils.slot_utils import generate_default_slots

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith('admin_'):
            return Admin.query.get(int(user_id.split('_')[1]))
        elif user_id.startswith('emp_'):
            return Employee.query.get(int(user_id.split('_')[1]))
        else:
            return User.query.get(int(user_id))

    # Register blueprints
    from routes import auth_bp, user_bp, admin_bp, employee_bp, main_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)

    # Create DB and seed admin
    with app.app_context():
        os.makedirs(app.config['FACE_FOLDER'], exist_ok=True)
        os.makedirs(app.config['CHAT_FOLDER'], exist_ok=True)
        os.makedirs(app.config['KNOWN_FACES_FOLDER'], exist_ok=True)
        db.create_all()

        # Create default admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', email='admin@nexusbank.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created: admin / admin123")

        # Generate slots
        try:
            count = generate_default_slots(60)
            if count:
                print(f"✅ Generated {count} default time slots")
        except Exception as e:
            print(f"Slot generation: {e}")

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
