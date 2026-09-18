from html import escape

from bs4 import BeautifulSoup
from rich.text import Text

from bible import util

from .common import render_section_titles


def render_nlt_verse(html: str) -> Text:
    """Render a single verse for the New Living Translation."""
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


def render_nlt_chapter(
    html: str,
    reference: str,
    summary: str | None = None,
    metadata: dict | None = None,
) -> Text:
    """Render a full chapter for the New Living Translation (NLT)."""
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

    # Unified paragraph loop
    for p in soup.find_all('p'):
        cls = p.get('class', [])
        if not cls:
            continue

        # Section titles (s1, s2, ms1)
        if any(c.startswith('s') or c.startswith('ms') for c in cls):
            title = p.get_text(strip=True)
            text.append(f'{title}\n\n', style='bold gold3')
            continue

        # Blank layout paragraph
        if 'b' in cls:
            text.append('\n')
            continue

        # Poetic lines (q1 / q2)
        if any(c.startswith('q') for c in cls):
            verse_span = p.find('span', class_='v')
            verse_num = (
                verse_span.get_text(strip=True) if verse_span else last_verse_num
            )
            if verse_num == last_verse_num:
                continue
            last_verse_num = verse_num

            line_text = p.get_text(' ', strip=True)
            if verse_num:
                line_text = line_text.replace(verse_num, '', 1).strip()

            indent = '  ' if 'q1' in cls else '      '
            num_style = 'bold bright_cyan' if 'q1' in cls else 'dim bright_cyan'
            text.append(f'{indent}{verse_num or ""} ', style=num_style)
            text.append(escape(line_text) + '\n', style='white')
            continue

        # Standard prose paragraphs (m, p, pmo, pm)
        if any(c in cls for c in ['m', 'p', 'pmo', 'pm']):
            paragraph_text = Text()
            for span in p.find_all('span', class_='v'):
                verse_num = span.get_text(strip=True)
                if verse_num == last_verse_num:
                    continue
                last_verse_num = verse_num

                verse_content_parts = []
                for sibling in span.next_siblings:
                    if getattr(sibling, 'name', None) == 'span' and 'v' in sibling.get(
                        'class', []
                    ):
                        break
                    if getattr(sibling, 'name', None) == 'span' and 'it' in sibling.get(
                        'class', []
                    ):
                        verse_content_parts.append(
                            (' ' + sibling.get_text(strip=True) + ' ', 'italic white')
                        )
                    elif isinstance(sibling, str):
                        verse_content_parts.append((sibling, 'white'))
                    elif getattr(sibling, 'name', None):
                        verse_content_parts.append(
                            (sibling.get_text(' ', strip=True), 'white')
                        )

                num_style = (
                    'bold bright_cyan' if not paragraph_text else 'dim bright_cyan'
                )
                paragraph_text.append(f'  {verse_num} ', style=num_style)
                for part, style in verse_content_parts:
                    paragraph_text.append(part.strip(), style=style)
                paragraph_text.append('\n')

            paragraph_text.append('\n')
            text.append(paragraph_text)
            text.append('\n')
            continue

    # Handle tables (inventory lists)
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
