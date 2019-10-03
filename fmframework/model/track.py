from fmframework.model.fm import LastFM, Wiki
from fmframework.model.album import Album
from fmframework.model.artist import Artist
from fmframework.util.console import Color


class Track(LastFM):
    def __init__(self,
                 name: str = None,
                 url: str = None,
                 mbid: str = None,
                 listeners: int = None,
                 play_count: int = None,
                 user_scrobbles: int = None,
                 wiki: Wiki = None,
                 album: Album = None,
                 artist: Artist = None,
                 ):
        super().__init__(name=name,
                         url=url,
                         mbid=mbid,
                         listeners=listeners,
                         play_count=play_count,
                         user_scrobbles=user_scrobbles,
                         wiki=wiki)
        self.album = album
        self.artist = artist

    def __str__(self):
        return f'{self.name} / {self.album} / {self.artist}'

    def __repr__(self):
        return super().__repr__() + Color.YELLOW + Color.BOLD + ' Track' + Color.END + \
               f': album({repr(self.album)}), artist({repr(self.artist)})'

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
