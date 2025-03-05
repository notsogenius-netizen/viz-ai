from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    This class defines the settings for the app
    """

    DB_URI: str

    model_config= SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()