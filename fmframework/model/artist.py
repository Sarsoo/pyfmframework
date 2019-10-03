from fmframework.util.console import Color
from fmframework.model.fm import LastFM, Wiki


class Artist(LastFM):
    def __init__(self,
                 name: str,
                 url: str = None,
                 mbid: str = None,
                 listeners: int = None,
                 play_count: int = None,
                 user_scrobbles: int = None,
                 wiki: Wiki = None):
        super().__init__(name=name,
                         url=url,
                         mbid=mbid,
                         listeners=listeners,
                         play_count=play_count,
                         user_scrobbles=user_scrobbles,
                         wiki=wiki)

    def __str__(self):
        return f'{self.name}'

    def __repr__(self):
        return super().__repr__() + Color.PURPLE + Color.BOLD + ' Artist' + Color.END