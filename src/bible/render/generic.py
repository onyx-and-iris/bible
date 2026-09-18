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
def render_generic_chapter(
    html: str,
    reference: str,
    summary: str | None = None,
    metadata: dict | None = None,
) -> Text:
    """Render a full chapter for unsupported Bible versions."""
    soup = BeautifulSoup(html, 'html.parser')
    soup = util.normalise_paragraph_classes(soup)
    text = Text()

    # Header block
    text.append(f'\n{reference}\n', style='bold gold3')
    text.append('─' * len(reference) + '\n', style='grey50')

    # Metadata block
    if metadata:
        meta_line = ' • '.join(f'{k.capitalize()}: {v}' for k, v in metadata.items())
        text.append(f'{meta_line}\n', style='dim white')

    # Chapter summary
    if summary:
        text.append(f'\n{summary}\n', style='italic grey70')
        text.append('─' * len(summary) + '\n\n', style='grey50')

    # Section titles
    for s in soup.find_all('p', class_='s'):
        title = s.get_text(strip=True)
        text.append(f'{title}\n\n', style='bold gold3')

    # Generic paragraph handling
    last_verse_num = None
    for p in soup.find_all('p'):
        cls = p.get('class', [])
        if not cls:
            continue

        # Section titles (already handled above, skip duplicates)
        if 's' in cls:
            continue

        verse_span = p.find('span', class_='v')
        verse_text = p.get_text(' ', strip=True)

        if verse_span:
            verse_num = verse_span.get_text(strip=True)
            if verse_num == last_verse_num:
                continue
            last_verse_num = verse_num
            verse_text = verse_text.replace(verse_num, '', 1).strip()
            text.append(f'  {verse_num} ', style='bold bright_cyan')

        text.append(escape(verse_text) + '\n', style='white')

    return text
