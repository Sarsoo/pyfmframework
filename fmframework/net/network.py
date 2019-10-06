import requests
from typing import Optional, List
from copy import deepcopy
import logging
from datetime import datetime, date, time, timedelta

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
            params['from'] = int(from_time.timestamp())
        if to_time is not None:
            params['to'] = int(to_time.timestamp())

        iterator = PageCollection(net=self, method='user.getrecenttracks', params=params, response_limit=limit)
        iterator.response_limit = limit + 1 if limit is not None else None
        iterator.load()

        items = iterator.items

        if items[0].get('@attr', {}).get('nowplaying', None):
            items.pop(0)

        return [self.parse_scrobble(i) for i in items[:limit]]

    def get_scrobbles_from_date(self,
                                input_date: date,
                                username: str = None,
                                limit: int = None) -> Optional[List[Scrobble]]:
        logger.info(f'getting {input_date} scrobbles for {self.username if username is None else username}')
        midnight = time(hour=0, minute=0, second=0)

        from_date = datetime.combine(date=input_date, time=midnight)
        to_date = datetime.combine(date=input_date + timedelta(days=1), time=midnight)

        scrobbles = self.get_recent_tracks(username=username, from_time=from_date, to_time=to_date, limit=limit)

        return scrobbles

    def get_scrobble_count_from_date(self,
                                     input_date: date,
                                     username: str = None,
                                     limit: int = None) -> int:
        logger.info(f'getting {input_date} scrobble count for {self.username if username is None else username}')

        scrobbles = self.get_scrobbles_from_date(input_date=input_date, username=username, limit=limit)

        if scrobbles:
            return len(scrobbles)
        else:
            return 0

    def get_track(self,
                  name: str,
                  artist: str,
                  username: str = None) -> Optional[Track]:
        logger.info(f'getting {name} / {artist} for {self.username if username is None else username}')

        params = {
            'track': name,
            'artist': artist,
            'user': self.username if username is None else username
        }

        resp = self.get_request('track.getInfo', params=params)

        if resp:
            return self.parse_track(resp['track'])
        else:
            logger.error('no response')

    def get_album(self,
                  name: str,
                  artist: str,
                  username: str = None) -> Optional[Album]:
        logger.info(f'getting {name} / {artist} for {self.username if username is None else username}')

        params = {
            'album': name,
            'artist': artist,
            'user': self.username if username is None else username
        }

        resp = self.get_request('album.getInfo', params=params)

        if resp:
            return self.parse_album(resp['album'])
        else:
            logger.error('no response')

    def get_artist(self,
                   name: str,
                   username: str = None) -> Optional[Artist]:
        logger.info(f'getting {name} for {self.username if username is None else username}')

        params = {
            'artist': name,
            'user': self.username if username is None else username
        }

        resp = self.get_request('artist.getInfo', params=params)

        if resp:
            return self.parse_artist(resp['artist'])
        else:
            logger.error('no response')

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
                      listeners=int(artist_dict["stats"].get('listeners', 0)),
                      play_count=int(artist_dict["stats"].get('playcount', 0)),
                      user_scrobbles=int(artist_dict["stats"].get('userplaycount', 0)),
                      wiki=self.parse_wiki(artist_dict['wiki']) if artist_dict.get('wiki', None) else None)

    def parse_album(self, album_dict) -> Album:
        return Album(name=album_dict.get('name', 'n/a'),
                     url=album_dict.get('url', 'n/a'),
                     mbid=album_dict.get('mbid', 'n/a'),
                     listeners=int(album_dict.get('listeners', 0)),
                     play_count=int(album_dict.get('playcount', 0)),
                     user_scrobbles=int(album_dict.get('userplaycount', 0)),
                     wiki=self.parse_wiki(album_dict['wiki']) if album_dict.get('wiki', None) else None,
                     artist=album_dict.get('artist'))

    def parse_track(self, track_dict) -> Track:
        track = Track(name=track_dict.get('name', 'n/a'),
                      url=track_dict.get('url', 'n/a'),
                      mbid=track_dict.get('mbid', 'n/a'),
                      listeners=int(track_dict.get('listeners', 0)),
                      play_count=int(track_dict.get('playcount', 0)),
                      user_scrobbles=int(track_dict.get('userplaycount', 0)),
                      wiki=self.parse_wiki(track_dict['wiki']) if track_dict.get('wiki', None) else None)

        if track_dict.get('album', None):
            track.album = self.parse_album(track_dict['album'])

        if track_dict.get('artist', None):
            track.album = self.parse_album(track_dict['artist'])

        return track

    @staticmethod
    def parse_scrobble(scrobble_dict) -> Scrobble:
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
        self.counter = 0

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
