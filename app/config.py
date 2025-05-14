from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    twilio_account_sid: str = 'your_account_sid_here'
    twilio_auth_token: str = 'your_auth_token_here'
    sqlite_uri: str = "sqlite:///multiagent.db"
    sqlserver_uri: str = "mssql+pyodbc://DesarrolloDatapro:7VZ8EW-tA4*J@192.168.40.17/ChatbotsDatapro?driver=ODBC+Driver+17+for+SQL+Server"
    chatbot_url: str = "http://localhost:5000"
    front_url: str = "http://localhost:3006"
    jwt_secret_key: str = "your_secret_key_here"
    jwt_refresh_secret_key: str = "your_refresh_key_here"
    jwt_reset_secret_key: str = "your_reset_key_here"
    sentry_dsn: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 120
    jwt_refresh_expiration: int = 1440
    jwt_reset_expiration: int = 1440
    max_assignments_per_agent: int = 3
    root_path: str = ""
    logging_level: str = "INFO"
    testing: bool = False
    environment: str = "development"
    smtp_sender: str = "your_email_here"
    smtp_password: str = "your_password_here"
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    redis_host: str = "localhost"
    redis_port: int = 6379
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()