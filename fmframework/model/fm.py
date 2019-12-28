from __future__ import annotations
from fmframework.util.console import Color
from datetime import datetime
from enum import Enum
from typing import List

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fmframework.model.track import Track


class Image:
    class Size(Enum):
        other = 0
        small = 1
        medium = 2
        large = 3
        extralarge = 4
        mega = 5

    def __init__(self, size: Size, link: str):
        self.size = size
        self.link = link

    def __str__(self):
        return f'{self.size.name} - {self.link}'


class Wiki:
    def __init__(self,
                 date: datetime = None,
                 summary: str = None,
                 content: str = None):
        self.date = date
        self.summary = summary
        self.content = content

    def __repr__(self):
        return Color.YELLOW + Color.BOLD + 'Wiki:' + Color.END + \
               f': {self.date}, {self.summary}, {self.content}'


class LastFM:
    def __init__(self,
                 name: str = None,
                 url: str = None,
                 mbid: str = None,
                 listeners: int = None,
                 play_count: int = None,
                 user_scrobbles: int = None,
                 wiki: Wiki = None,
                 images: List[Image] = None):
        self.name = name
        self.url = url
        self.mbid = mbid
        self.listeners = listeners
        self.play_count = play_count
        self.user_scrobbles = user_scrobbles
        self.wiki = wiki
        self.images = images

    def __str__(self):
        return self.name

    def __repr__(self):
        return Color.RED + Color.BOLD + 'LastFM' + Color.END + \
               f': {self.name}, user({self.user_scrobbles}), play_count({self.play_count}), ' \
                f'listeners({self.listeners}), wiki({self.wiki})'


class WeeklyChart:
    def __init__(self, from_time, to_time):
        self.from_secs = from_time
        self.to_secs = to_time

    @property
    def from_date(self):
        return datetime.fromtimestamp(self.from_secs)

    @property
    def to_date(self):
        return datetime.fromtimestamp(self.to_secs)

    def __str__(self):
        return f'{self.from_secs} -> {self.to_secs}'


class Scrobble:
    def __init__(self,
                 track: Track = None,
                 time: datetime = None):
        self.track = track
        self.time = time

    def __str__(self):
        return self.track

    def __repr__(self):
        return Color.BLUE + Color.BOLD + 'Scrobble' + Color.END + f': {self.time} {repr(self.track)}'
