import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nexus-bank-secret-2024-ultra-secure')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///nexusbank.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your_email@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your_app_password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME', 'nexusbank@gmail.com')

    # Uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    FACE_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'faces')
    CHAT_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'chat')
    KNOWN_FACES_FOLDER = os.path.join(os.path.dirname(__file__), 'known_faces')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # OTP
    OTP_EXPIRY_MINUTES = 5
