import argparse
import asyncio
import typing
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.theme import Theme
from textual.widgets import Footer, Header, Input, Link, LoadingIndicator, Static

from bible.logging import LogOutputType, configure_logging
from bible.mixins import BibleLookupMixin, ReferenceParserMixin
from bible.render import RenderMode, generate_summary, get_renderer
from bible.settings import settings
from bible.sqlite import init_db, load_json

from . import util
from .exceptions import BibleTUIFetchError
from .settings_modal import SettingsModal


class BibleTUI(BibleLookupMixin, ReferenceParserMixin, App):
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
        ('n', 'next_chapter', 'Next chapter'),
        ('ctrl+n', 'next_chapter', 'Next chapter'),
        ('p', 'prev_chapter', 'Previous chapter'),
        ('ctrl+p', 'prev_chapter', 'Previous chapter'),
        ('j', 'next_chapter', 'Next chapter'),
        ('ctrl+j', 'next_chapter', 'Next chapter'),
        ('k', 'prev_chapter', 'Previous chapter'),
        ('ctrl+k', 'prev_chapter', 'Previous chapter'),
    ]

    def __init__(self, theme_override: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.theme_override = theme_override
        self.current_bible_name = settings.tui.BIBLE_NAME
        self.current_book_name = settings.tui.BOOK_NAME
        self.active_theme = settings.tui.THEME
        self.chapter_renderer = get_renderer(
            self.current_bible_name, RenderMode.CHAPTER
        )
        self.verse_renderer = get_renderer(self.current_bible_name, RenderMode.VERSE)

        init_db()
        self.call_later(self.initialise_bible_list)

    async def initialise_bible_list(self) -> Any:
        """Ensure the list of Bibles is cached."""
        return await self.load_or_fetch_bibles()

    async def initialise_book_list(self) -> Any:
        """Ensure the list of books for the selected Bible is cached."""
        bible = self.find_bible(self.current_bible_name)
        return await self.load_or_fetch_books(bible)

    async def initialise_chapter_list(self) -> Any:
        """Ensure the list of chapters for the selected book is cached."""
        bible = self.find_bible(self.current_bible_name)
        book = self.find_book(self.current_bible_name, self.current_book_name)
        return await self.load_or_fetch_chapters(bible, book)

    async def fetch_multiple(self, chapters: list[int], verses: list[int] | None):
        """Fetch multiple chapters or verses concurrently."""
        tasks = []

        for chapter in chapters:
            if verses:
                for verse in verses:
                    # Each task resolves IDs and fetches independently
                    tasks.append(self.fetch_chapter_or_verse(str(chapter), str(verse)))
            else:
                tasks.append(self.fetch_chapter_or_verse(str(chapter)))

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Pair results with their reference
        output = []
        idx = 0
        for chapter in chapters:
            if verses:
                for verse in verses:
                    output.append(('verse', chapter, verse, results[idx]))
                    idx += 1
            else:
                output.append(('chapter', chapter, None, results[idx]))
                idx += 1

        return output

    async def fetch_chapter_or_verse(
        self, chapter_number: str, verse_number: str | None = None
    ):
        bible = self.find_bible(self.current_bible_name)
        book = self.find_book(self.current_bible_name, self.current_book_name)
        chapters = await self.load_or_fetch_chapters(bible, book)
        chapter = self.find_chapter(chapters, chapter_number)

        if verse_number:
            verses = await self.load_or_fetch_verses(
                bible, chapter, self.current_book_name
            )
            verse_meta = self.find_verse(
                verses, self.current_book_name, chapter_number, verse_number
            )
            return await self.load_or_fetch_verse_content(
                bible, book, chapter, verse_meta
            )

        return await self.load_or_fetch_chapter_content(bible, book, chapter)

    async def fetch_verse_meta(self, chapter_number: str, verse_number: str):
        bible = self.find_bible(self.current_bible_name)
        book = self.find_book(self.current_bible_name, self.current_book_name)
        chapters = await self.load_or_fetch_chapters(bible, book)
        chapter = self.find_chapter(chapters, chapter_number)

        verses = await self.load_or_fetch_verses(bible, chapter, self.current_book_name)
        verse_meta = self.find_verse(
            verses, self.current_book_name, chapter_number, verse_number
        )

        return await self.load_or_fetch_verse_content(bible, book, chapter, verse_meta)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.input = Input(
            placeholder='Enter book chapter or book chapter:verse (e.g., Genesis 1, Genesis 1:1)',
            id='search',
        )
        self.spinner = LoadingIndicator(id='spinner')
        self.spinner.display = False

        yield Header()
        yield self.input
        yield self.spinner
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
            f'📖 Current Bible: {self.current_bible_name}\n'
            'Type a reference or press B to list books.'
        )

        theme_name = self.active_theme.lower()

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

        bible_names = sorted([bible.get('name', 'Unknown') for bible in bibles])
        formatted = '\n'.join(bible_names)
        self.query_one('#content', Static).update(
            f'📚 Available Bibles:\n\n{formatted}'
        )

    async def action_list_books(self) -> None:
        """List all books for the current Bible."""

        key = f'books:list:{self.current_bible_name}'
        books = load_json(key)
        if not books:
            books = await self.initialise_book_list()

        book_names = [book.get('name', 'Unknown') for book in books]
        formatted = '\n'.join(book_names)
        self.query_one('#content', Static).update(
            f'📚 Books in {self.current_bible_name}:\n\n{formatted}'
        )

    async def action_next_chapter(self) -> None:
        """Navigate to the next chapter if available."""
        next_info = getattr(self, 'next_chapter', None)
        if not next_info:
            self.query_one('#content', Static).update('⚠️ No next chapter available.')
            return

        book = next_info.get('bookId')
        chapter = next_info.get('number')

        # Skip intros or invalid chapter identifiers
        if not chapter or not chapter.isdigit():
            self.query_one('#content', Static).update('⚠️ No next chapter available.')
            return

        self.input.value = f'{book} {chapter}'
        await self.action_show_reference()

    async def action_prev_chapter(self) -> None:
        """Navigate to the previous chapter if available."""
        prev_info = getattr(self, 'prev_chapter', None)
        if not prev_info:
            self.query_one('#content', Static).update(
                '⚠️ No previous chapter available.'
            )
            return

        book = prev_info.get('bookId')
        chapter = prev_info.get('number')

        # Skip intros or invalid chapter identifiers
        if not chapter or not chapter.isdigit():
            self.query_one('#content', Static).update(
                '⚠️ No previous chapter available.'
            )
            return

        self.input.value = f'{book} {chapter}'
        await self.action_show_reference()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user search input."""
        await self.action_show_reference()

    async def action_show_reference(self) -> None:
        query = self.input.value.strip()

        if not query:
            self.query_one('#content', Static).update(
                '❌ Please enter a reference or command.'
            )
            return

        if query.lower() == 'list bibles':
            await self.action_list_bibles()
            self.input.value = ''
            return

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
            self.current_book_name = book
        except ValueError as e:
            self.query_one('#content', Static).update(f'❌ {e}')
            return

        # If no specific chapters or verses are provided, load all chapters for the current book.
        if chapters is None and verses is None:
            chapters_key = (
                f'chapters:list:{self.current_bible_name}:{self.current_book_name}'
            )
            chapters_cache = load_json(chapters_key)
            if not chapters_cache:
                chapters_cache = await self.initialise_chapter_list()
            chapters = [ch['number'] for ch in chapters_cache]

        try:
            self.spinner.display = True
            items = await self.fetch_multiple(chapters, verses)
        except BibleTUIFetchError as e:
            self.query_one('#content', Static).update(f'⚠️ {e}')
            self.spinner.display = False
            return
        finally:
            self.spinner.display = False

        output = Text()

        for kind, chapter, verse, data in items:
            if isinstance(data, Exception):
                ref = (
                    f'{self.current_book_name} {chapter}'
                    if verse is None
                    else f'{self.current_book_name} {chapter}:{verse}'
                )
                output.append(f'⚠️ Error fetching {ref}: {data}\n')
                continue

            self.next_chapter = data.get('next')
            self.prev_chapter = data.get('previous')
            self.current_chapter = chapter

            html = data.get('content', '')

            if kind == 'verse':
                rendered = self.verse_renderer(html)
                output.append(rendered)
            else:
                summary = generate_summary(html)
                metadata = {
                    'Book': self.current_book_name,
                    'Chapter': chapter,
                    'Verses': data.get('verseCount'),
                }
                rendered = self.chapter_renderer(
                    html,
                    f'{self.current_book_name} {chapter}',
                    summary,
                    metadata,
                )
                output.append(rendered)

            output.append('\n')

        self.query_one('#content', Static).update(output)

    async def __validate_book(self, book: str) -> bool:
        books_key = f'books:list:{self.current_bible_name}'
        cached_books = load_json(books_key) or await self.initialise_book_list()
        target = util.normalise_user_book_input(book)
        return any(
            util.normalise_user_book_input(b.get('name', '')) == target
            for b in cached_books
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Bible TUI — interact with API.Bible')
    parser.add_argument('--theme', type=str, help='Specify the theme (light or dark)')
    parser.add_argument(
        '--log-level',
        default=settings.tui.LOG_LEVEL,
        type=str,
        choices=[
            'trace',
            'debug',
            'info',
            'success',
            'warning',
            'error',
            'critical',
        ],
        help='Specify the log level (e.g., info, debug, warning)',
    )
    parser.add_argument(
        '--log-output',
        default=settings.tui.LOG_OUTPUT,  # Change this if loguru conflicts with the TUI.
        type=str,
        choices=['console', 'file', 'both'],
        help='Specify the log output type (console, file, both)',
    )
    parser.add_argument(
        '--log-path',
        default=settings.tui.LOG_PATH,
        type=str,
        help='Specify the log file path (default is app.log)',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log_output = {
        'console': [LogOutputType.CONSOLE],
        'file': [LogOutputType.FILE],
        'both': [LogOutputType.BOTH],
    }.get(args.log_output, [LogOutputType.FILE])
    configure_logging(args.log_level, log_output, args.log_path)

    app = BibleTUI(theme_override=args.theme)
    app.run()
