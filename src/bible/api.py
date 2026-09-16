from niquests import AsyncSession

from .settings import settings


class BibleAPI:
    async def __aenter__(self):
        self.session = AsyncSession(
            base_url=settings.shared.ENDPOINT,
            headers={'api-key': settings.shared.API_KEY},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def get(self, path: str, params: dict | None = None):
        response = await self.session.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def get_bibles(self):
        return await self.get('/v1/bibles')

    async def get_books(self, bible_id: str):
        return await self.get(f'/v1/bibles/{bible_id}/books')

    async def get_chapters(self, bible_id: str, book_id: str):
        return await self.get(f'/v1/bibles/{bible_id}/books/{book_id}/chapters')

    async def get_verses(self, bible_id: str, chapter_id: str):
        return await self.get(f'/v1/bibles/{bible_id}/chapters/{chapter_id}/verses')

    async def get_verse(self, bible_id: str, verse_id: str):
        return await self.get(f'/v1/bibles/{bible_id}/verses/{verse_id}')

    async def get_chapter(self, bible_id: str, chapter_id: str):
        return await self.get(f'/v1/bibles/{bible_id}/chapters/{chapter_id}')

    async def get_passage(self, bible_id: str, passage_id: str):
        return await self.get(f'/v1/bibles/{bible_id}/passages/{passage_id}')

    async def get_section(self, bible_id: str, section_id: str):
        return await self.get(f'/v1/bibles/{bible_id}/sections/{section_id}')
