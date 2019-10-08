from typing import List
from fmframework.model.fm import LastFM, Wiki, Image
from fmframework.model.album import Album
from fmframework.model.artist import Artist
from fmframework.util.console import Color


class Track(LastFM):
    def __init__(self,
                 name: str = None,
                 url: str = None,
                 mbid: str = None,
                 listeners: int = 0,
                 play_count: int = 0,
                 user_scrobbles: int = 0,
                 wiki: Wiki = None,
                 album: Album = None,
                 artist: Artist = None,
                 images: List[Image] = None):
        super().__init__(name=name,
                         url=url,
                         mbid=mbid,
                         listeners=listeners,
                         play_count=play_count,
                         user_scrobbles=user_scrobbles,
                         wiki=wiki,
                         images=images)
        self.album = album
        self.artist = artist

    def __str__(self):
        return f'{self.name} / {self.album} / {self.artist}'

    def __repr__(self):
        return Color.YELLOW + Color.BOLD + 'Track' + Color.END + \
               f': {self.name} album({repr(self.album)}), artist({repr(self.artist)}) ' + super().__repr__()

    @staticmethod
    def wrap(name: str = None,
             artist: str = None,
             album: str = None,
             album_artist: str = None,
             url: str = None,
             mbid: str = None,
             listeners: int = None,
             play_count: int = None,
             user_scrobbles: int = None):
        return Track(name=name,
                     album=Album.wrap(name=album, artist=album_artist),
                     artist=Artist(artist),
                     url=url,
                     mbid=mbid,
                     listeners=listeners,
                     play_count=play_count,
                     user_scrobbles=user_scrobbles)
