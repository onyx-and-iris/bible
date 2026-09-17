from bs4 import BeautifulSoup


def normalise_paragraph_classes(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Normalise paragraph class names across different Bible translations.
    Ensures consistent 's' for section titles and 'p' for verse paragraphs.
    """
    for p in soup.find_all('p'):
        classes = p.get('class', [])
        if not classes:
            continue

        # Section titles (e.g. s1, s2 → s)
        if any(cls.startswith('s') for cls in classes):
            p['class'] = ['s']

        # Verse paragraphs (e.g. m, b, li1, li2 → p)
        elif any(cls.startswith(('m', 'b', 'li', 'p')) for cls in classes):
            p['class'] = ['p']

    return soup


def normalise_user_book_input(name: str) -> str:
    return name.lower().replace('.', '').replace(',', '').replace(' ', '').strip()
