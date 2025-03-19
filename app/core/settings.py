from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    This class defines the settings for the app
    """

    DB_URI: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    LLM_URI: str


    model_config= SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()