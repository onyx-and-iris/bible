from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from bible.render import RenderMode, get_renderer
from bible.sqlite import get_cached

from . import util


class SettingsModal(ModalScreen):
    """Modal window for editing persistent Bible settings."""

    def compose(self) -> ComposeResult:
        app = self.app

        yield Vertical(
            Label('Set Bible', id='bible_label'),
            Input(
                value=app.current_bible_name, placeholder='Default Bible', id='bible'
            ),
            Label('Set Theme', id='theme_label'),
            Input(value=app.active_theme, placeholder='Default Theme', id='theme'),
            Button('Save', id='save', variant='success'),
            Button('Cancel', id='cancel', variant='error'),
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handler for button press events in the settings modal.

        This method handles the logic for the "Save" and "Cancel" buttons.
        If "Cancel" is pressed, the modal is dismissed without saving changes.
        If "Save" is pressed, the input is validated and, if valid, the settings are updated and persisted.

        Args:
            event (Button.Pressed): The button press event that triggered this handler.
        """
        if event.button.id == 'cancel':
            self.dismiss()
            return

        if event.button.id == 'save':
            bible = self.query_one('#bible', Input).value.strip()

            bible_input = self.query_one('#bible', Input)
            if not await self.__validate_bible_name(bible):
                bible_input.value = f'Invalid Bible name: {bible}'
                bible_input.cursor_position = 0
                bible_input.selection = (0, 0)
                return

            theme_input = self.query_one('#theme', Input)
            theme = theme_input.value.strip()

            if not await self.__validate_theme(theme):
                theme_input.value = f'Invalid theme: {theme}'
                theme_input.cursor_position = 0
                theme_input.selection = (0, 0)
                return

            self.app.current_bible_name = bible
            self.app.active_theme = theme
            self.app.chapter_renderer = get_renderer(bible, RenderMode.CHAPTER)
            self.app.verse_renderer = get_renderer(bible, RenderMode.VERSE)
            await self.apply_theme(theme)

            util.save_env_value('BIBLE_TUI_BIBLE_NAME', bible)
            util.save_env_value('BIBLE_TUI_THEME', theme)

            self.dismiss()

    async def __validate_bible_name(self, bible: str) -> bool:
        """Validate the Bible name input."""
        bibles = get_cached('bibles:list')
        if bibles is None:
            return False
        return bible in bibles

    async def __validate_theme(self, theme: str) -> bool:
        return theme in self.app.available_themes

    async def apply_theme(self, theme_name: str):
        self.app.theme = theme_name

        await self.__validate_theme(theme_name)

        self.app.refresh_css(self.app.css_path)

        self.refresh()
