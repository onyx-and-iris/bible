import asyncio

from bible.api import BibleAPI
from bible.settings import settings
from bible.sqlite import cache_json, load_json

from .exceptions import BibleTUIFetchError


async def fetch_multiple(app, book: str, chapters: list[int], verses: list[int] | None):
    """Fetch multiple chapters or verses concurrently."""
    tasks = []

    for chapter in chapters:
        if verses:
            for verse in verses:
                # Each task resolves IDs and fetches independently
                tasks.append(fetch_chapter_or_verse(app, str(chapter), str(verse)))
        else:
            tasks.append(fetch_chapter_or_verse(app, str(chapter)))

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Pair results with their reference
    output = []
    idx = 0
    for chapter in chapters:
        if verses:
            for verse in verses:
                output.append(('verse', chapter, verse, results[idx]))
                idx += 1
        else:
            output.append(('chapter', chapter, None, results[idx]))
            idx += 1

    return output


async def fetch_chapter_or_verse(
    app,
    chapter_number: str,
    verse_number: str | None = None,
):
    """Fetch chapter or verse from cache or API."""

    # --- Cache key ---
    if verse_number:
        key = (
            f'verses:content:{settings.BIBLE_NAME}:'
            f'{settings.BOOK_NAME}:{chapter_number}:{verse_number}'
        )
    else:
        key = (
            f'chapters:content:{settings.BIBLE_NAME}:'
            f'{settings.BOOK_NAME}:{chapter_number}'
        )

    cached = load_json(key)
    if cached:
        return cached

    # --- Bible lookup ---
    bibles = load_json('bibles:list')
    bible = next((b for b in bibles if b.get('name') == settings.BIBLE_NAME), None)
    if not bible:
        raise BibleTUIFetchError(f"Bible '{settings.BIBLE_NAME}' not found in cache.")
    bible_id = bible['id']

    # --- Chapter list lookup ---
    chapter_list = load_json(
        f'chapters:list:{settings.BIBLE_NAME}:{settings.BOOK_NAME}'
    )
    if not chapter_list:
        chapter_list = await app.initialise_chapter_list()

    chapter_item = next(
        (ch for ch in chapter_list if str(ch.get('number')) == str(chapter_number)),
        None,
    )
    if not chapter_item:
        raise BibleTUIFetchError(f"Chapter '{chapter_number}' not found in cache.")
    chapter_id = chapter_item['id']

    # --- API fetch ---
    async with BibleAPI() as api:
        if verse_number:
            verse_meta = await fetch_verse_meta(
                bible_id,
                chapter_number,
                verse_number,
                chapter_id,
            )
            verse_id = verse_meta.get('id')
            response = await api.get_verse(bible_id, verse_id)
        else:
            response = await api.get_chapter(bible_id, chapter_id)

        data = response.get('data', {})
        if data:
            cache_json(key, data)
        return data


async def fetch_verse_meta(
    bible_id: str,
    chapter_number: str,
    verse_number: str,
    chapter_id: str,
):
    """Fetch metadata for a specific verse from cache or API."""

    # --- Cache key for verse content ---
    key = (
        f'verses:content:{settings.BIBLE_NAME}:'
        f'{settings.BOOK_NAME}:{chapter_number}:{verse_number}'
    )
    cached = load_json(key)
    if cached:
        return cached

    # --- Load or fetch verse list ---
    verses_key = (
        f'verses:list:{settings.BIBLE_NAME}:{settings.BOOK_NAME}:{chapter_number}'
    )
    verses = load_json(verses_key)

    if not verses:
        async with BibleAPI() as api:
            response = await api.get_verses(bible_id, chapter_id)
            verses = response.get('data', [])
            if not verses:
                raise BibleTUIFetchError(
                    f"Unable to fetch list of verses for chapter '{chapter_number}' "
                    'from the API.'
                )
            cache_json(verses_key, verses)

    # --- Find verse metadata ---
    target_ref = f'{settings.BOOK_NAME} {chapter_number}:{verse_number}'

    verse_meta = next(
        (v for v in verses if isinstance(v, dict) and v.get('reference') == target_ref),
        None,
    )

    if not verse_meta:
        raise BibleTUIFetchError(f'Verse {target_ref} not found.')

    # --- Fetch verse content ---
    async with BibleAPI() as api:
        response = await api.get_verse(bible_id, verse_meta.get('id'))
        data = response.get('data', {})
        if data:
            cache_json(key, data)
        return data
