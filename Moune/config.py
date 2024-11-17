import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'oD9amP_AE5-_iCr0_FC4gczlywfa_NcUT9dr9WD3VzY'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'moune_ecommerce.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Removed the comma
