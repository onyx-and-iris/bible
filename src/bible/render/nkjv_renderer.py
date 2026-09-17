from html import escape

from bs4 import BeautifulSoup
from rich.text import Text

from .common import render_section_titles


def render_nkjv_verse(html: str) -> Text:
    """Render a single verse for NKJV."""
    soup = BeautifulSoup(html, 'html.parser')
    text = Text()

    render_section_titles(soup, text)

    for p in soup.find_all('p', class_=['p', 'q', 'q1', 'q2']):
        verse_num = p.find('span', class_='v')
        verse_text = p.get_text(' ', strip=True)
        if verse_num:
            num = verse_num.get_text(strip=True)
            verse_text = verse_text.replace(num, '', 1).strip()
            text.append(f'{num} ', style='bold cyan')
        text.append(escape(verse_text) + '\n', style='white')

    return text


def render_nkjv_chapter(
    html: str,
    reference: str,
    summary: str | None = None,
    metadata: dict | None = None,
) -> Text:
    """
    Render a full Bible chapter with rich formatting, summaries, and metadata.
    - summary: short overview of the chapter's theme
    - metadata: dictionary with contextual info (e.g., {"book": "Genesis", "chapter": 1, "verses": 31})
    """
    soup = BeautifulSoup(html, 'html.parser')
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

    # Paragraphs with verses
    for p in soup.find_all('p', class_='p'):
        paragraph_text = Text()

        for span in p.find_all('span', class_='v'):
            verse_num = span.get_text(strip=True)
            verse_content_parts = []

            # Collect siblings until next verse span
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

            # Build verse line
            paragraph_text.append(f'  {verse_num} ', style='bold bright_cyan')
            for part, style in verse_content_parts:
                if paragraph_text and not paragraph_text.plain.endswith(' '):
                    paragraph_text.append(' ')
                paragraph_text.append(part.strip(), style=style)
            paragraph_text.append('\n')

        text.append(paragraph_text)
        text.append('\n')

    return text
