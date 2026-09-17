from html import escape

from bs4 import BeautifulSoup
from rich.text import Text

from .common import render_section_titles


def render_niv_verse(html: str) -> Text:
    """Render a single verse for NIV 2011."""
    soup = BeautifulSoup(html, 'html.parser')
    text = Text()

    render_section_titles(soup, text)

    for p in soup.find_all('p', class_=['p', 'pmo', 'pm', 'lh', 'lf']):
        verse_num = p.find('span', class_='v')
        verse_text = p.get_text(' ', strip=True)
        if verse_num:
            num = verse_num.get_text(strip=True)
            verse_text = verse_text.replace(num, '', 1).strip()
            text.append(f'{num} ', style='bold cyan')
        text.append(escape(verse_text) + '\n', style='white')

    return text


def render_niv_chapter(
    html: str,
    reference: str,
    summary: str | None = None,
    metadata: dict | None = None,
) -> Text:
    soup = BeautifulSoup(html, 'html.parser')
    text = Text()

    # Header
    text.append(f'\n{reference}\n', style='bold gold3')
    text.append('─' * len(reference) + '\n', style='grey50')

    if metadata:
        meta_line = ' • '.join(f'{k.capitalize()}: {v}' for k, v in metadata.items())
        text.append(f'{meta_line}\n', style='dim white')

    if summary:
        text.append(f'\n{summary}\n', style='italic grey70')
        text.append('─' * len(summary) + '\n\n', style='grey50')

    # Section titles
    for s in soup.find_all('p', class_=lambda c: c and c.startswith('s')):
        title = s.get_text(strip=True)
        text.append(f'{title}\n\n', style='bold gold3')

    last_verse_num = None

    # Unified pass over all paragraphs
    for p in soup.find_all('p'):
        cls = p.get('class', [])
        cls_str = ' '.join(cls)

        # Blank layout paragraph
        if 'b' in cls_str:
            text.append('\n')
            continue

        # Inventory header (lh)
        if 'lh' in cls_str:
            verse_span = p.find('span', class_='v')
            if verse_span:
                last_verse_num = verse_span.get_text(strip=True)
            header_text = p.get_text(' ', strip=True)
            if last_verse_num:
                header_text = header_text.replace(last_verse_num, '', 1).strip()
            text.append(f'  {last_verse_num or ""} ', style='bold bright_cyan')
            text.append(f'{escape(header_text)}\n', style='white')
            continue

        # Inventory list item (li1 or litl paragraph)
        if 'li1' in cls_str or 'litl' in cls_str:
            verse_span = p.find('span', class_='v')
            quantity_span = p.find('span', class_='litl')
            item_text = p.get_text(' ', strip=True)

            if verse_span:
                last_verse_num = verse_span.get_text(strip=True)
                item_text = item_text.replace(last_verse_num, '', 1).strip()

            qty = None
            if quantity_span:
                qty = quantity_span.get_text(strip=True)
                item_text = item_text.replace(qty, '', 1).strip()

            # Indented bullet line
            text.append('      • ', style='white')
            text.append(f'{escape(item_text)}', style='white')
            if qty:
                text.append(f' {qty}', style='bold gold3')
            text.append('\n')
            continue

        # Standard verse paragraphs (p, pmo, pm, lf) — EXCLUDING li1/litl
        if any(c in cls_str for c in ['p', 'pmo', 'pm', 'lf']) and not any(
            x in cls_str for x in ['li1', 'litl']
        ):
            paragraph_text = Text()

            for span in p.find_all('span', class_='v'):
                verse_num = span.get_text(strip=True)
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

                paragraph_text.append(f'  {verse_num} ', style='bold bright_cyan')
                for part, style in verse_content_parts:
                    if paragraph_text and not paragraph_text.plain.endswith(' '):
                        paragraph_text.append(' ')
                    paragraph_text.append(part.strip(), style=style)
                paragraph_text.append('\n')

            text.append(paragraph_text)
            text.append('\n')
            continue

    return text
