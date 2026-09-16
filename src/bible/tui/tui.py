import argparse
import typing
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.theme import Theme
from textual.widgets import Footer, Header, Input, Link, Static

from bible.api import BibleAPI
from bible.logging import configure_logging
from bible.render import generate_summary, render_chapter, render_verse
from bible.settings import settings
from bible.sqlite import cache_json, get_cached, init_db, load_json

from . import util
from .exceptions import BibleTUIFetchError
from .fetch import fetch_chapter_or_verse, fetch_multiple
from .settings_modal import SettingsModal


class BibleTUI(App):
    """A Textual TUI for browsing and reading Bible chapters."""

    CSS_PATH = 'tui.tcss'
    TITLE = 'Bible TUI'
    BINDINGS: typing.ClassVar[list[tuple[str, str, str]]] = [
        ('q', 'quit', 'Quit'),
        ('s', 'open_settings', 'Settings'),
        ('ctrl+s', 'open_settings', 'Settings'),
        ('b', 'list_books', 'List Books'),
        ('ctrl+b', 'list_books', 'List Books'),
        ('l', 'list_bibles', 'List Bibles'),
        ('ctrl+l', 'list_bibles', 'List Bibles'),
    ]

    def __init__(self, theme_override: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.theme_override = theme_override
        init_db()
        self.call_later(self.initialise_bible_list)

    async def initialise_bible_list(self):
        """Ensure the list of Bibles is cached."""
        bibles_key = 'bibles:list'
        if get_cached(bibles_key):
            return

        async with BibleAPI() as api:
            response = await api.get_bibles()
            data = response.get('data', [])
            if not data:
                raise BibleTUIFetchError('Unable to fetch list of Bibles from the API.')
            cache_json(bibles_key, data)

    async def initialise_book_list(self) -> Any:
        """Ensure the list of books for the selected Bible is cached."""
        books_key = f'books:list:{settings.BIBLE_NAME}'

        if cached_books := load_json(books_key):
            return cached_books

        # --- Bible lookup ---
        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == settings.BIBLE_NAME), None)
        if not bible:
            raise BibleTUIFetchError(
                f"Bible '{settings.BIBLE_NAME}' not found in cache."
            )

        bible_id = bible['id']

        async with BibleAPI() as api:
            response = await api.get_books(bible_id)
            data = response.get('data', [])
            if not data:
                raise BibleTUIFetchError(
                    f"Unable to fetch list of books for Bible '{settings.BIBLE_NAME}' from the API."
                )
            cache_json(books_key, data)

        return data

    async def initialise_chapter_list(self) -> Any:
        """Ensure the list of chapters for the selected book is cached."""
        chapters_key = f'chapters:list:{settings.BIBLE_NAME}:{settings.BOOK_NAME}'

        if cached_chapters := load_json(chapters_key):
            return cached_chapters

        # --- Bible lookup ---
        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == settings.BIBLE_NAME), None)
        if not bible:
            raise BibleTUIFetchError(
                f"Bible '{settings.BIBLE_NAME}' not found in cache."
            )

        bible_id = bible['id']

        # --- Book lookup ---
        books_key = f'books:list:{settings.BIBLE_NAME}'
        books = load_json(books_key)

        if not books:
            books = await self.initialise_book_list()

        book = next((bk for bk in books if bk.get('name') == settings.BOOK_NAME), None)
        if not book:
            raise BibleTUIFetchError(f"Book '{settings.BOOK_NAME}' not found in cache.")

        book_id = book['id']

        # --- Fetch chapters ---
        async with BibleAPI() as api:
            response = await api.get_chapters(bible_id, book_id)
            data = response.get('data', [])
            if not data:
                raise BibleTUIFetchError(
                    f'Unable to fetch list of chapters for {settings.BOOK_NAME} from the API.'
                )
            cache_json(chapters_key, data)

        return data

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.input = Input(
            placeholder='Enter book chapter or book chapter:verse (e.g., Genesis 1, Genesis 1:1)',
            id='search',
        )

        yield Header()
        yield self.input
        yield VerticalScroll(Static('Welcome to the Bible TUI!', id='content'))
        yield Link(
            'Powered by API.Bible',
            url='https://api.bible',
            tooltip='Click me',
        )
        yield Footer()

    async def on_mount(self) -> None:
        """Initial setup when the app starts."""
        self.query_one('#content', Static).update(
            f'📖 Current Bible: {settings.BIBLE_NAME}\n'
            'Type a reference or press B to list books.'
        )

        theme_name = settings.THEME.lower()

        """
        # If it's a built-in theme, just apply it
        if theme_name in self.available_themes:
            self.theme = theme_name
            return
        """

        light_theme = Theme(
            name='onyx-light',
            surface='#f5f5f5',
            foreground='#1e1e1e',
            accent='#4a90e2',
            primary='#4a90e2',
            secondary='#6bb3ff',
        )
        self.register_theme(light_theme)

        dark_theme = Theme(
            name='onyx-dark',
            surface='#1e1e1e',
            foreground='#e6e6e6',
            accent='#4a90e2',
            primary='#4a90e2',
            secondary='#6bb3ff',
        )
        self.register_theme(dark_theme)

        self.theme = theme_name

    async def action_open_settings(self) -> None:
        await self.push_screen(SettingsModal())

    async def action_quit(self) -> None:
        self.exit()

    async def action_list_bibles(self) -> None:
        """List all available Bibles."""

        key = 'bibles:list'
        bibles = load_json(key)
        if not bibles:
            bibles = await self.initialise_bible_list()

        bible_names = [bible.get('name', 'Unknown') for bible in bibles]
        formatted = '\n'.join(bible_names)
        self.query_one('#content', Static).update(
            f'📚 Available Bibles:\n\n{formatted}'
        )

    async def action_list_books(self) -> None:
        """List all books for the current Bible."""

        key = f'books:list:{settings.BIBLE_NAME}'
        books = load_json(key)
        if not books:
            books = await self.initialise_book_list()

        book_names = [book.get('name', 'Unknown') for book in books]
        formatted = '\n'.join(book_names)
        self.query_one('#content', Static).update(
            f'📚 Books in {settings.BIBLE_NAME}:\n\n{formatted}'
        )

    async def action_show_verse(self) -> None:
        verse_input = self.input.value.strip()
        try:
            book, chapter_verse = verse_input.split(maxsplit=1)
            settings.BOOK_NAME = book
            chapter, verse = chapter_verse.split(':')
            try:
                verse = await fetch_chapter_or_verse(self, chapter, verse)
                if not verse:
                    self.query_one('#content', Static).update('⚠️ Verse not found.')
                    return
            except BibleTUIFetchError as e:
                self.query_one('#content', Static).update(f'⚠️ {e!s}')
                return
        except ValueError:
            self.query_one('#content', Static).update(
                '❌ Invalid format. Use: Genesis 1:1'
            )
            return

        html = verse.get('content', '')
        text = render_verse(html)
        self.query_one('#content', Static).update(text)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user search input."""
        await self.action_show_reference()

    async def action_show_reference(self) -> None:
        query = self.input.value.strip()

        if query.lower() == 'list books':
            await self.action_list_books()
            self.input.value = ''
            return

        try:
            book, chapters, verses = util.parse_reference(query)
            if not await self.__validate_book(book):
                await self.action_list_books()
                raise ValueError(
                    f"Book '{book}' not found. Enter 'list books' to see available books."
                )
            settings.BOOK_NAME = book
        except ValueError as e:
            self.query_one('#content', Static).update(f'❌ {e}')
            return

        try:
            items = await fetch_multiple(self, book, chapters, verses)
        except BibleTUIFetchError as e:
            self.query_one('#content', Static).update(f'⚠️ {e}')
            return

        # Render everything
        output = Text()

        for kind, chapter, verse, data in items:
            if isinstance(data, Exception):
                ref = (
                    f'{book} {chapter}'
                    if verse is None
                    else f'{book} {chapter}:{verse}'
                )
                output.append(f'⚠️ Error fetching {ref}: {data}\n')
                continue

            html = data.get('content', '')

            if kind == 'verse':
                rendered = render_verse(html)
                output.append(rendered)
            else:
                summary = generate_summary(html)
                metadata = {
                    'Book': book,
                    'Chapter': chapter,
                    'Verses': data.get('verseCount'),
                }
                rendered = render_chapter(
                    html,
                    f'{book} {chapter}',
                    summary,
                    metadata,
                )
                output.append(rendered)

            output.append('\n')

        self.query_one('#content', Static).update(output)

    async def __validate_book(self, book: str) -> bool:
        books_key = f'books:list:{settings.BIBLE_NAME}'
        cached_books = load_json(books_key)
        if not cached_books:
            cached_books = await self.initialise_book_list()
        return book in [b.get('name') for b in cached_books]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Bible TUI — interact with API.Bible')
    parser.add_argument('--theme', type=str, help='Specify the theme (light or dark)')
    parser.add_argument(
        '--log-level',
        type=str,
        help='Specify the log level (e.g., info, debug, warning)',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    configure_logging(args.log_level or settings.LOG_LEVEL)

    app = BibleTUI(theme_override=args.theme)
    app.run()
