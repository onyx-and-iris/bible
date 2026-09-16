from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BIBLE_NAME: str
    BOOK_NAME: str = 'Genesis'
    ENDPOINT: str = 'https://rest.api.bible'
    API_KEY: str
    CACHE_EXPIRY_DAYS: int = 30
    THEME: str = 'onyx-dark'
    LOG_LEVEL: str = 'info'
    DB_PATH: Path = Path.home() / '.cache' / 'bible' / 'bible_cache.db'

    model_config = SettingsConfigDict(
        env_file=[Path('.env'), Path.home() / '.config' / 'bible' / 'config.env'],
        env_file_encoding='utf-8',
        env_prefix='BIBLE_',
        validate_assignment=True,
    )


settings = Settings()
