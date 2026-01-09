class Settings():
    # Application settings
    APP_NAME: str = "Nightly"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    VERSION: str = "v1.0.0"

    # Database settings
    DATABASE_URL: str

    # Security settings
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 300
    ALGORITHM: str = "HS256"

    # CORS settings
    ALLOWED_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
