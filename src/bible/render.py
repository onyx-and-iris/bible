from bs4 import BeautifulSoup
from rich.markup import escape
from rich.text import Text

from . import util


def generate_summary(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    soup = util.normalize_paragraph_classes(soup)

    # Prefer section title if available
    section = soup.find('p', class_='s')
    if section:
        title = section.get_text(strip=True)
        return f'{title} — a summary of key events and teachings.'

    # Otherwise, use the first sentence of the first paragraph
    first_para = soup.find('p', class_='p')
    if first_para:
        text = first_para.get_text(' ', strip=True)
        first_sentence = text.split('.')[0]
        return f'{first_sentence.strip()}.'

    return 'Summary unavailable.'


def render_chapter(
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
    soup = util.normalize_paragraph_classes(soup)
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


def render_verse(html: str) -> Text:
    """Render a single verse with rich formatting."""
    soup = BeautifulSoup(html, 'html.parser')
    soup = util.normalize_paragraph_classes(soup)
    text = Text()

    # Section titles
    for s in soup.find_all('p', class_='s'):
        title = s.get_text(strip=True)
        text.append(f'\n{title}\n', style='bold gold3')

    # Verse paragraphs
    for p in soup.find_all('p', class_='p'):
        verse_num = p.find('span', class_='v')
        verse_text = p.get_text(' ', strip=True)

        if verse_num:
            num = verse_num.get_text(strip=True)
            # Remove the verse number from the paragraph text
            verse_text = verse_text.replace(num, '', 1).strip()
            text.append(f'{num} ', style='bold cyan')

        text.append(escape(verse_text) + '\n', style='white')

    return text
