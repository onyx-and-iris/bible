from html import escape

from bs4 import BeautifulSoup
from rich.text import Text

from bible import util


def generate_summary(html: str) -> str:
    """Generate a short, automatic summary for a Bible chapter."""
    soup = BeautifulSoup(html, 'html.parser')
    soup = util.normalise_paragraph_classes(soup)

    section = soup.find('p', class_='s')
    if section:
        title = section.get_text(strip=True)
        return f'{title} — a summary of key events and teachings.'

    first_para = soup.find('p', class_='p')
    if first_para:
        text = first_para.get_text(' ', strip=True)
        first_sentence = text.split('.')[0]
        return f'{first_sentence.strip()}.'

    return 'Summary unavailable.'


def render_section_titles(soup: BeautifulSoup, text: Text):
    for s in soup.find_all('p', class_=lambda c: c and c.startswith('s')):
        title = s.get_text(strip=True)
        text.append(f'\n{title}\n', style='bold gold3')


def render_paragraphs(soup: BeautifulSoup, text: Text, classes=('p', 'm', 'b', 'li')):
    for p in soup.find_all('p', class_=lambda c: c and c.startswith(classes)):
        verse_num = p.find('span', class_='v')
        verse_text = p.get_text(' ', strip=True)
        if verse_num:
            num = verse_num.get_text(strip=True)
            verse_text = verse_text.replace(num, '', 1).strip()
            text.append(f'{num} ', style='bold cyan')
        text.append(escape(verse_text) + '\n', style='white')


def render_poetic_line(p, last_verse_num):
    cls = p.get('class', [])
    verse_span = p.find('span', class_='v')

    # q1 = new verse
    if verse_span:
        verse_num = verse_span.get_text(strip=True)
        line_text = p.get_text(' ', strip=True).replace(verse_num, '', 1).strip()
        indent = '  '
        num_style = 'bold bright_cyan'
        return verse_num, [
            (f'{indent}{verse_num} ', num_style),
            (escape(line_text) + '\n', 'white'),
        ]

    # q2/q3/q4 = continuation
    indent = '      ' if 'q2' in cls else '          '
    line_text = p.get_text(' ', strip=True)
    return last_verse_num, [(f'{indent}{escape(line_text)}\n', 'white')]
