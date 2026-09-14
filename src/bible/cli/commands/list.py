from typing import final

from clypi import Command, arg
from loguru import logger
from typing_extensions import override

from bible import console
from bible.sqlite import load_json


class List(Command):
    """List all available Bibles."""

    contains: str = arg(
        None,
        help='Filter Bibles by name containing this string',
        group='Filter',
    )
    sort: bool = arg(
        False,
        help='Sort the Bibles alphabetically',
        group='Filter',
    )

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by Bible.API — https://api.bible.com'

    @override
    async def run(self):
        bibles = load_json('bibles:list')
        if self.sort:
            bibles = sorted(bibles, key=lambda x: x.get('name', '').lower())
        seen = set()
        for bible in bibles:
            if (
                self.contains
                and self.contains.lower() not in bible.get('name', '').lower()
            ):
                continue

            if bible.get('name', '') in seen:
                logger.debug(f'Skipping duplicate Bible: {bible.get("name", "")}')
                continue

            console.out.print(f'{bible.get("name", "")}')
            seen.add(bible.get('name', ''))
