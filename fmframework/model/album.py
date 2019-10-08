from typing import List
from fmframework.model.fm import LastFM, Wiki, Image
from fmframework.model.artist import Artist
from fmframework.util.console import Color


class Album(LastFM):
    def __init__(self,
                 name: str = None,
                 url: str = None,
                 mbid: str = None,
                 listeners: int = None,
                 play_count: int = None,
                 user_scrobbles: int = None,
                 wiki: Wiki = None,
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
        self.artist = artist

    def __str__(self):
        return f'{self.name} / {self.artist}'

    def __repr__(self):
        return Color.DARKCYAN + Color.BOLD + 'Album' + Color.END + f': {self.name} artist({repr(self.artist)}) ' \
               + super().__repr__()

    @staticmethod
    def wrap(name: str = None,
             artist: str = None,
             url: str = None,
             mbid: str = None,
             listeners: int = None,
             play_count: int = None,
             user_scrobbles: int = None):
        return Album(name=name,
                     artist=Artist(name=artist),
                     url=url,
                     mbid=mbid,
                     listeners=listeners,
                     play_count=play_count,
                     user_scrobbles=user_scrobbles)
