from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List


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


@dataclass
class Wiki:
    published: datetime = None
    summary: str = None
    content: str = None

    def __post_init__(self):
        if isinstance(self.published, str):
            self.published = datetime.strptime(self.published, '%d %b %Y, %H:%M')


@dataclass
class LastFM:
    name: str = None
    url: str = None
    mbid: str = None
    listeners: int = None
    play_count: int = None
    user_scrobbles: int = None
    wiki: Wiki = None
    images: List[Image] = None

    def __str__(self):
        return self.name


@dataclass
class Artist(LastFM):
    def __str__(self):
        return f'{self.name}'


@dataclass
class Album(LastFM):
    artist: Artist = None

    def __str__(self):
        return f'{self.name} / {self.artist}'


@dataclass
class Track(LastFM):
    album: Album = None
    artist: Artist = None

    def __str__(self):
        return f'{self.name} / {self.album} / {self.artist}'


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


@dataclass
class Scrobble:
    track: Track = None
    time: datetime = None

    def __str__(self):
        return self.track
