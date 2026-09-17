from enum import IntEnum

from .generic import render_generic_chapter, render_generic_verse
from .niv_renderer import render_niv_chapter, render_niv_verse
from .nkjv_renderer import render_nkjv_chapter, render_nkjv_verse


class RenderMode(IntEnum):
    CHAPTER = 1
    VERSE = 2


RENDERERS = {
    'New International Version 2011': {
        RenderMode.CHAPTER: render_niv_chapter,
        RenderMode.VERSE: render_niv_verse,
    },
    'New King James Version': {
        RenderMode.CHAPTER: render_nkjv_chapter,
        RenderMode.VERSE: render_nkjv_verse,
    },
    '_default': {
        RenderMode.CHAPTER: render_generic_chapter,
        RenderMode.VERSE: render_generic_verse,
    },
}


def get_renderer(bible_name: str, mode: RenderMode = RenderMode.CHAPTER):
    entry = RENDERERS.get(bible_name, RENDERERS['_default'])
    return entry.get(mode, RENDERERS['_default'][mode])
