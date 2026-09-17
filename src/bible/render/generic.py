from html import escape

from bs4 import BeautifulSoup
from rich.text import Text

from bible import util

from .common import render_section_titles


# --- Verse renderer ---------------------------------------------------------
def render_generic_verse(html: str) -> Text:
    """Render a single verse for unsupported Bible versions."""
    soup = BeautifulSoup(html, 'html.parser')
    soup = util.normalise_paragraph_classes(soup)
    text = Text()

    # Section titles (shared logic)
    render_section_titles(soup, text)

    for p in soup.find_all('p'):
        verse_num = p.find('span', class_='v')
        verse_text = p.get_text(' ', strip=True)

        if verse_num:
            num = verse_num.get_text(strip=True)
            verse_text = verse_text.replace(num, '', 1).strip()
            text.append(f'{num} ', style='bold cyan')

        text.append(escape(verse_text) + '\n', style='white')

    return text


# --- Chapter renderer -------------------------------------------------------
def render_generic_chapter(html: str) -> Text:
    """Render a full chapter for unsupported Bible versions."""
    soup = BeautifulSoup(html, 'html.parser')
    text = Text()

    render_section_titles(soup, text)

    # Handle all paragraph types generically
    for p in soup.find_all('p'):
        verse_num = p.find('span', class_='v')
        verse_text = p.get_text(' ', strip=True)

        if verse_num:
            num = verse_num.get_text(strip=True)
            verse_text = verse_text.replace(num, '', 1).strip()
            text.append(f'{num} ', style='bold cyan')

        text.append(escape(verse_text) + '\n', style='white')

    return text
