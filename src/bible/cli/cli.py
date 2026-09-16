from typing import final

from clypi import ClypiConfig, Command, arg, configure
from typing_extensions import override

from bible.logging import LogOutputType, configure_logging
from bible.mixins import BibleLookupMixin
from bible.settings import settings
from bible.sqlite import init_db

from .commands import Book, List


class BibleCli(BibleLookupMixin, Command):
    """Bible CLI — interact with API.Bible"""

    subcommand: Book | List | None
    api_key: str = arg(
        settings.cli.API_KEY,
        help='The API key for the Bible CLI',
        group='Connection',
    )
    bible_name: str = arg(
        settings.cli.BIBLE_NAME,
        help='The name of the Bible to retrieve books from',
        group='Connection',
    )
    log_level: str = arg(
        settings.cli.LOG_LEVEL,
        help='The log level for the Bible CLI',
        group='Logging',
    )
    log_output: str = arg(
        settings.cli.LOG_OUTPUT,
        help='The log output type for the Bible CLI (console, file, both)',
        group='Logging',
    )
    log_path: str = arg(
        settings.cli.LOG_PATH,
        help='The log file path for the Bible CLI',
        group='Logging',
    )

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by API.Bible — https://api.bible.com'

    @override
    async def pre_run_hook(self):
        """Hook to run before the main command execution."""

        configure_logging(
            self.log_level,
            {
                'console': [LogOutputType.CONSOLE],
                'file': [LogOutputType.FILE],
                'both': [LogOutputType.BOTH],
            }.get(self.log_output, [LogOutputType.FILE]),
            self.log_path,
        )
        init_db()

        await self.load_or_fetch_bibles()

    @override
    async def run(self):
        """Run the appropriate subcommand based on user input."""

        if self.subcommand is None:
            self.print_help()
            return

        return await self.subcommand.astart()


def main():
    configure(ClypiConfig())

    cli = BibleCli()
    cli.parse().start()
