from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Payment Processing API"
    app_version: str = "1.0.1"
    debug: bool = False
    
    # Lithic API Configuration
    lithic_api_key: str
    lithic_api_base_url: str = "https://api.lithic.com"
    
    # Database Configuration
    database_url: str = "sqlite:///./payments.db"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # JWT Configuration
    jwt_secret_key: str = "your-super-secret-jwt-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    use_mock_lithic: bool = False
    
    # Email Configuration
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = "noreply@advancia.com"
    sender_password: str = ""
    app_url: str = "http://localhost:8000"
    email_test_mode: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
