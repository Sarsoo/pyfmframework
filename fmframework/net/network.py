import requests
from typing import Optional, List
from copy import deepcopy
import logging
from datetime import datetime

from fmframework.model.fm import Scrobble, Wiki
from fmframework.model.track import Track
from fmframework.model.album import Album
from fmframework.model.artist import Artist

logger = logging.getLogger(__name__)


class Network:

    def __init__(self, username, api_key):
        self.api_key = api_key
        
        self.username = username
        self.retry_counter = 0

    def get_request(self,
                    method: str,
                    params: dict = None) -> Optional[dict]:
       
        data = {
                "format": 'json',
                "method": method,
                "api_key": self.api_key,
                }
        if params is not None:
            data.update(params)

        req = requests.get('http://ws.audioscrobbler.com/2.0/', params=data)

        if 200 <= req.status_code < 300:
            logger.debug(f'{method} {req.status_code}')
            return req.json()
        else:
            resp = req.json()

            code = resp.get('error', None)
            message = resp.get('message', None)

            if code:
                if code == 8:
                    if self.retry_counter < 5:
                        self.retry_counter += 1
                        logger.warning(f'{method} {req.status_code} {code} {message} retyring')
                        return self.get_request(method, params)
                    else:
                        self.retry_counter = 0
                        logger.error(f'{method} {req.status_code} {code} {message} retry limit reached')
                else:
                    logger.error(f'{method} {req.status_code} {code} {message} retry limit reached')
            else:
                if message:
                    logger.error(f'{method} {req.status_code} {message}')
                else:
                    logger.error(f'{method} {req.status_code}')

    def get_recent_tracks(self,
                          username: str = None,
                          limit: int = None,
                          from_time: datetime = None,
                          to_time: datetime = None) -> Optional[List[Scrobble]]:
        if limit is not None:
            logger.info(f'pulling {limit} tracks')
        else:
            logger.info(f'pulling all tracks')

        params = {
            'user': self.username if username is None else username
        }

        if from_time is not None:
            params['from'] = from_time.timestamp()
        if to_time is not None:
            params['to'] = to_time.timestamp()

        iterator = PageCollection(net=self, method='user.getrecenttracks', params=params, response_limit=limit)
        iterator.response_limit = limit
        iterator.load()

        return [self.parse_scrobble(i) for i in iterator.items]

    @staticmethod
    def parse_wiki(wiki_dict) -> Optional[Wiki]:
        if wiki_dict:
            return Wiki(date=datetime.strptime(wiki_dict.get('published', None), '%d %b %Y, %H:%M'),
                        summary=wiki_dict.get('summary', None),
                        content=wiki_dict.get('content', None))
        else:
            return None

    def parse_artist(self, artist_dict) -> Artist:
        return Artist(name=artist_dict.get('name', 'n/a'),
                      url=artist_dict.get('url', None),
                      mbid=artist_dict.get('mbid', None),
                      listeners=artist_dict.get('listeners', None),
                      play_count=artist_dict.get('playcount', None),
                      user_scrobbles=artist_dict.get('userplaycount', None),
                      wiki=self.parse_wiki(artist_dict['wiki']) if artist_dict.get('wiki', None) else None)

    def parse_album(self, album_dict) -> Album:
        return Album(name=album_dict.get('name', 'n/a'),
                     url=album_dict.get('url', 'n/a'),
                     mbid=album_dict.get('mbid', 'n/a'),
                     listeners=album_dict.get('listeners', 'n/a'),
                     play_count=album_dict.get('playcount', 'n/a'),
                     user_scrobbles=album_dict.get('userplaycount', 'n/a'),
                     wiki=self.parse_wiki(album_dict['wiki']) if album_dict.get('wiki', None) else None,
                     artist=album_dict.get('artist'))

    def parse_track(self, track_dict):
        track = Track(name=track_dict.get('name', 'n/a'),
                      url=track_dict.get('url', 'n/a'),
                      mbid=track_dict.get('mbid', 'n/a'),
                      listeners=track_dict.get('listeners', 'n/a'),
                      play_count=track_dict.get('playcount', 'n/a'),
                      user_scrobbles=track_dict.get('userplaycount', 'n/a'),
                      wiki=self.parse_wiki(track_dict['wiki']) if track_dict.get('wiki', None) else None)

        if track_dict.get('album', None):
            track.album = self.parse_album(track_dict['album'])

        if track_dict.get('artist', None):
            track.album = self.parse_album(track_dict['artist'])

        return track

    @staticmethod
    def parse_scrobble(scrobble_dict):
        album = None
        if scrobble_dict.get('album', None):
            album = Album(name=scrobble_dict['album'].get('#text', 'n/a'),
                          mbid=scrobble_dict['album'].get('mbid', None))

        artist = None
        if scrobble_dict.get('artist', None):
            artist = Artist(name=scrobble_dict['artist'].get('#text', 'n/a'),
                            mbid=scrobble_dict['artist'].get('mbid', None))

        if artist is not None and album is not None:
            if album.artist is None:
                album.artist = artist

        track = Track(name=scrobble_dict.get('name', 'n/a'),
                      album=album,
                      artist=artist,
                      mbid=scrobble_dict.get('mbid', None),
                      url=scrobble_dict.get('url', None))

        return Scrobble(track=track, time=datetime.fromtimestamp(int(scrobble_dict['date']['uts'])))


class PageCollection:
    def __init__(self,
                 net: Network,
                 method: str,
                 params: dict = None,
                 page_limit: int = 50,
                 response_limit: int = 50):
        self.net = net
        self.method = method
        self.params = params
        self.pages: List[Page] = []
        self.page_limit = page_limit
        self.response_limit = response_limit
        self.counter = 1

    def __len__(self):
        length = 0
        for page in self.pages:
            length += len(page.items)
        return length

    @property
    def total(self):
        if len(self.pages) > 0:
            return self.pages[0].total
        return 0

    @property
    def items(self):
        items = []
        for page in self.pages:
            items += page.items
        return items[:self.response_limit]

    def load(self):
        if self.response_limit:
            tracker = True
            while len(self) < self.response_limit and tracker:
                page = self.iterate()
                if len(page) == 0:
                    tracker = False
                else:
                    self.pages.append(page)
        else:
            tracker = True
            while tracker:
                page = self.iterate()
                if len(page) == 0:
                    tracker = False
                else:
                    self.pages.append(page)

    def iterate(self):
        logger.debug(f'iterating {self.method}')
        self.counter += 1

        params = deepcopy(self.params)

        params.update({
            'limit': self.page_limit,
            'page': self.counter
        })
        resp = self.net.get_request(method=self.method, params=params)

        if resp:
            return self.parse_page(resp)
            # if len(page) > 0:
            #     if self.response_limit:
            #         if len(self) < self.response_limit:
            #             self.iterate()
            #     else:
            #         self.iterate()
        else:
            logger.error('no response')

    def add_page(self, page_dict):
        page = self.parse_page(page_dict)
        self.pages.append(page)
        return page

    @staticmethod
    def parse_page(page_dict):
        first_value = list(page_dict.values())[0]
        items = list(first_value.values())[1]
        return Page(
            number=first_value['@attr'].get('page', None),
            size=first_value['@attr'].get('perPage', None),
            total=first_value['@attr'].get('total', None),
            total_pages=first_value['@attr'].get('totalPages', None),
            items=items)


class Page:
    def __init__(self,
                 number: int,
                 size: int,
                 total: int,
                 total_pages: int,
                 items: list):
        self.number = number
        self.size = size
        self.total = total
        self.total_pages = total_pages
        self.items = items

    def __len__(self):
        return len(self.items)
