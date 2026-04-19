from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Medical Exam Simulator"
    DATABASE_URL: str = "postgresql://user:password@localhost/medical_sim"
    SECRET_KEY: str = "a_very_secret_key_for_jwt_tokens"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    OPENAI_API_KEY: str = ""
    ADMIN_SECRET_KEY: str = "change_me_in_production"
    SUPER_ADMIN_KEY: str = "super_secret_for_remote_management"

    class Config:
        env_file = ".env"

settings = Settings()
