from typing import final

from clypi import Command, arg
from loguru import logger
from typing_extensions import override

from bible.api import BibleAPI
from bible.logging import configure_logging
from bible.settings import settings
from bible.sqlite import cache_json, get_cached, init_db

from .commands import Book, List


class BibleCli(Command):
    """Bible CLI — interact with API.Bible"""

    subcommand: Book | List | None
    api_key: str = arg(
        settings.API_KEY,
        help='The API key for the Bible CLI',
        group='Connection',
    )
    bible_name: str = arg(
        settings.BIBLE_NAME,
        help='The name of the Bible to retrieve books from',
        group='Connection',
    )
    log_level: str = arg(
        settings.LOG_LEVEL,
        help='The log level for the Bible CLI',
        group='Connection',
    )

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by API.Bible — https://api.bible.com'

    @override
    async def pre_run_hook(self):
        """Hook to run before the main command execution."""

        configure_logging(self.log_level)
        init_db()

        key = 'bibles:list'
        if get_cached(key):
            logger.debug('Using cached list of Bibles.')
            return

        logger.debug('Fetching list of Bibles from the API.')
        async with BibleAPI() as api:
            response = await api.get_bibles()
            data = response.get('data', [])
            if not data:
                raise ValueError('Unable to fetch list of Bibles from the API.')
            cache_json(key, data)

    @override
    async def run(self):
        """Run the appropriate subcommand based on user input."""


def main():
    cli = BibleCli()
    cli.parse().start()
