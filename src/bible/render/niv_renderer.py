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

    # NIV section titles (class s1, s2, etc.)
    for s in soup.find_all('p', class_=lambda c: c and c.startswith('s')):
        title = s.get_text(strip=True)
        text.append(f'{title}\n\n', style='bold gold3')

    last_verse_num = None

    # Helper: detect section headers like "36 The priests:"
    def is_section_header(p):
        cls = p.get('class', [])
        if 'p' not in cls:
            return False
        verse_span = p.find('span', class_='v')
        if not verse_span:
            return False
        txt = p.get_text(' ', strip=True)
        return ':' in txt  # genealogical/census section header

    # Helper: detect inventory header (Ezra 1)
    def is_inventory_header(p):
        return 'lh' in p.get('class', [])

    # Helper: detect inventory item (Ezra 1)
    def is_inventory_item(p):
        return 'li1' in p.get('class', []) and p.find('span', class_='litl')

    # Helper: detect genealogical/census list item (Ezra 2, Neh 7)
    def is_section_list_item(p):
        return 'li1' in p.get('class', []) and not p.find('span', class_='litl')

    # Helper: detect nested list item (Ezra 10 li2)
    def is_nested_list_item(p):
        return 'li2' in p.get('class', [])

    # Main paragraph loop
    for p in soup.find_all('p'):
        cls = p.get('class', [])
        cls_str = ' '.join(cls)

        # Blank layout paragraph
        if 'b' in cls_str:
            text.append('\n')
            continue

        # ─────────────────────────────────────────────
        # INVENTORY HEADER (Ezra 1)
        # ─────────────────────────────────────────────
        if is_inventory_header(p):
            verse_span = p.find('span', class_='v')
            if verse_span:
                last_verse_num = verse_span.get_text(strip=True)

            header_text = p.get_text(' ', strip=True)
            if last_verse_num:
                header_text = header_text.replace(last_verse_num, '', 1).strip()

            text.append(f'  {last_verse_num or ""} ', style='bold bright_cyan')
            text.append(f'{escape(header_text)}\n', style='white')
            continue

        # ─────────────────────────────────────────────
        # INVENTORY ITEM (Ezra 1)
        # ─────────────────────────────────────────────
        if is_inventory_item(p):
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

            text.append('      • ', style='white')
            text.append(escape(item_text), style='white')
            if qty:
                text.append(f' {qty}', style='bold gold3')
            text.append('\n')
            continue

        # ─────────────────────────────────────────────
        # SECTION HEADER (Ezra 2, Nehemiah 7)
        # ─────────────────────────────────────────────
        if is_section_header(p):
            verse_span = p.find('span', class_='v')
            if verse_span:
                last_verse_num = verse_span.get_text(strip=True)

            txt = p.get_text(' ', strip=True)
            if last_verse_num:
                txt = txt.replace(last_verse_num, '', 1).strip()

            text.append(f'  {last_verse_num} ', style='bold bright_cyan')
            text.append(f'{escape(txt)}\n', style='white')
            continue

        # ─────────────────────────────────────────────
        # SECTION LIST ITEM (Ezra 2 genealogies)
        # ─────────────────────────────────────────────
        if is_section_list_item(p):
            item_text = p.get_text(' ', strip=True)
            verse_span = p.find('span', class_='v')

            if verse_span:
                last_verse_num = verse_span.get_text(strip=True)
                item_text = item_text.replace(last_verse_num, '', 1).strip()

            text.append('      • ', style='white')
            text.append(escape(item_text), style='white')
            text.append('\n')
            continue

        # ─────────────────────────────────────────────
        # NESTED LIST ITEM (Ezra 10 li2)
        # ─────────────────────────────────────────────
        if is_nested_list_item(p):
            item_text = p.get_text(' ', strip=True)
            verse_span = p.find('span', class_='v')

            if verse_span:
                last_verse_num = verse_span.get_text(strip=True)
                item_text = item_text.replace(last_verse_num, '', 1).strip()

            text.append('          • ', style='white')  # deeper indent for li2
            text.append(escape(item_text), style='white')
            text.append('\n')
            continue

        # ─────────────────────────────────────────────
        # POETIC LINES (q1 / q2)
        # ─────────────────────────────────────────────
        if 'q1' in cls:
            verse_span = p.find('span', class_='v')
            verse_num = (
                verse_span.get_text(strip=True) if verse_span else last_verse_num
            )
            if verse_span:
                last_verse_num = verse_num

            line_text = p.get_text(' ', strip=True)
            if verse_num:
                line_text = line_text.replace(verse_num, '', 1).strip()

            text.append(f'  {verse_num or ""} ', style='bold bright_cyan')
            text.append(escape(line_text) + '\n', style='white')
            continue

        if 'q2' in cls:
            line_text = p.get_text(' ', strip=True)
            text.append('      ' + escape(line_text) + '\n', style='white')
            continue

        # ─────────────────────────────────────────────
        # STANDARD VERSE PARAGRAPHS
        # ─────────────────────────────────────────────
        if any(c in cls_str for c in ['p', 'pmo', 'pm', 'lf']):
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

                # render each verse on its own line
                paragraph_text.append(f'  {verse_num} ', style='bold bright_cyan')
                for part, style in verse_content_parts:
                    paragraph_text.append(part.strip(), style=style)
                paragraph_text.append('\n')

            paragraph_text.append('\n')
            text.append(paragraph_text)
            text.append('\n')
            continue

    return text
