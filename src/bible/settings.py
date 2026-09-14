from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BIBLE_NAME: str
    BOOK_NAME: str = 'Genesis'
    ENDPOINT: str = 'https://rest.api.bible'
    API_KEY: str
    CACHE_EXPIRY_DAYS: int = 30
    THEME: str = 'dark'

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_prefix='BIBLE_',
        validate_assignment=True,
    )


settings = Settings()
