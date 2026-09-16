from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_FILES = [Path('.env'), Path.home() / '.config' / 'bible' / 'config.env']


class SharedSettings(BaseSettings):
    API_KEY: str = ''
    ENDPOINT: str = 'https://rest.api.bible'
    CACHE_EXPIRY_DAYS: int = 30
    DB_PATH: Path = Path.home() / '.cache' / 'bible' / 'bible_cache.db'

    BIBLE_NAME: str = ''

    model_config = SettingsConfigDict(
        env_file=CONFIG_FILES, env_prefix='BIBLE_', extra='ignore'
    )


class CLISettings(BaseSettings):
    API_KEY: str | None = None
    ENDPOINT: str | None = None
    CACHE_EXPIRY_DAYS: int | None = None
    DB_PATH: Path | None = None

    BIBLE_NAME: str | None = None
    BOOK_NAME: str = 'Genesis'
    THEME: str = 'onyx-dark'
    LOG_LEVEL: str = 'info'
    LOG_OUTPUT: str = 'console'
    LOG_PATH: str = 'app.log'

    model_config = SettingsConfigDict(
        env_file=CONFIG_FILES, env_prefix='BIBLE_CLI_', extra='ignore'
    )


class TUISettings(BaseSettings):
    API_KEY: str | None = None
    ENDPOINT: str | None = None
    CACHE_EXPIRY_DAYS: int | None = None
    DB_PATH: Path | None = None

    BIBLE_NAME: str | None = None
    BOOK_NAME: str = 'Genesis'
    THEME: str = 'onyx-dark'
    LOG_LEVEL: str = 'info'
    LOG_OUTPUT: str = 'console'
    LOG_PATH: str = 'app.log'

    model_config = SettingsConfigDict(
        env_file=CONFIG_FILES, env_prefix='BIBLE_TUI_', extra='ignore'
    )


class AppSettings(BaseSettings):
    shared: SharedSettings = SharedSettings()
    cli: CLISettings = CLISettings()
    tui: TUISettings = TUISettings()

    model_config = SettingsConfigDict(extra='ignore')

    @model_validator(mode='after')
    def merge(self):
        # Fill missing CLI values from shared
        for field in type(self.shared).model_fields:
            if getattr(self.cli, field) is None:
                setattr(self.cli, field, getattr(self.shared, field))

        # Fill missing TUI values from shared
        for field in type(self.shared).model_fields:
            if getattr(self.tui, field) is None:
                setattr(self.tui, field, getattr(self.shared, field))

        return self


settings = AppSettings()
