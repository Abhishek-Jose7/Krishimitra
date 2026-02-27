import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    # Fallback to SQLite for local development if no URL provided
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///krishimitra.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Groq API key for AI Overseer explanation layer
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
    SUPABASE_PROJECT_REF = os.environ.get('SUPABASE_PROJECT_REF', '')
