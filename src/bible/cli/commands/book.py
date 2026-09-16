from typing import final

from clypi import Command, Positional, arg
from typing_extensions import override

from bible.mixins import BibleLookupMixin
from bible.sqlite import load_json

from .book_commands import Chapter, Chapters, List, Verse, Verses


class Book(BibleLookupMixin, Command):
    """Manage Bible books, including listing and retrieving chapters."""

    subcommand: List | Chapter | Chapters | Verse | Verses | None
    bible_name: str = arg(inherited=True)
    book_name: Positional[str] = arg(
        None, help='The name of the Bible book to retrieve'
    )

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by API.Bible — https://api.bible.com'

    @override
    async def pre_run_hook(self):
        """Hook to run before the main command execution."""
        if not self.bible_name:
            raise ValueError("The 'bible_name' flag is required.")

        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == self.bible_name), None)
        if not bible:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        await self.load_or_fetch_books(bible)

    @override
    async def run(self):
        """Main execution method for the Book command."""

        if not self.book_name:
            self.print_help()
            return

        if self.subcommand is None:
            sub = Chapters(bible_name=self.bible_name, book_name=self.book_name)
            return await sub.astart()

        return await self.subcommand.astart()
