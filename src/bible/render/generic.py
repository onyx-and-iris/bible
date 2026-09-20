from html import escape

from bs4 import BeautifulSoup
from rich.text import Text

from bible import util

from .common import render_poetic_line, render_section_titles


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

    last_verse_num = None
    blank_count = 0

    for p in soup.find_all('p'):
        cls = p.get('class', []) or []

        # SECTION TITLES (s, s1, s2, ms1, etc.)
        if any(c.startswith('s') or c.startswith('ms') for c in cls):
            title = p.get_text(strip=True)
            text.append('\n')  # spacing before section title
            text.append(f'{title}\n\n', style='bold gold3')
            blank_count = 0
            continue

        # BLANK PARAGRAPHS (collapse multiples)
        if 'b' in cls:
            blank_count += 1
            if blank_count == 1:
                text.append('\n')
            continue
        blank_count = 0

        # POETIC LINES (q1, q2)
        if any(c.startswith('q') for c in cls):
            last_verse_num, parts = render_poetic_line(p, last_verse_num)
            for text_part, style in parts:
                text.append(text_part, style=style)
            continue

        # LIST ITEMS (li1, li2)
        if any(c.startswith('li') for c in cls):
            item_text = p.get_text(' ', strip=True)
            text.append('      • ', style='white')
            text.append(escape(item_text) + '\n', style='white')
            continue

        # TABLE ROWS (inventory lists)
        if p.find_parent('table'):
            # handled after main loop
            continue

        # GENERIC VERSE PARAGRAPHS
        verse_span = p.find('span', class_='v')
        verse_text = p.get_text(' ', strip=True)

        if verse_span:
            verse_num = verse_span.get_text(strip=True)
            if verse_num != last_verse_num:
                last_verse_num = verse_num
                verse_text = verse_text.replace(verse_num, '', 1).strip()
                text.append(f'  {verse_num} ', style='bold bright_cyan')
            text.append(escape(verse_text) + '\n', style='white')
        else:
            # fallback plain paragraph
            text.append(escape(verse_text) + '\n', style='white')

    # TABLE HANDLING (generic)
    for table in soup.find_all('table'):
        for row in table.find_all('row'):
            cells = row.find_all('cell')
            if len(cells) == 2:
                item = cells[0].get_text(' ', strip=True)
                qty = cells[1].get_text(' ', strip=True)
                text.append('      • ', style='white')
                text.append(escape(item), style='white')
                text.append(f' {qty}\n', style='bold gold3')
        text.append('\n')

    return text
