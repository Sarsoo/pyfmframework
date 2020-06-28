import requests
from dataclasses import dataclass
from typing import Optional, List, Union
from copy import deepcopy
import logging
import os
from enum import Enum
from datetime import datetime, date, time, timedelta

import numpy as np
import cv2

from fmframework.model import Album, Artist, Image, Wiki, WeeklyChart, Scrobble, Track
from fmframework import config_directory

logger = logging.getLogger(__name__)


class ImageSizeNotAvailableException(Exception):
    pass


@dataclass
class LastFMNetworkException(Exception):
    http_code: int
    error_code: int
    message: str = None

    def __str__(self):
        return "Last.fm Network Exception: (%s/%s) %s" % (self.http_code, self.error_code, self.message)


class Network:

    class Range(Enum):
        OVERALL = 'overall'
        WEEK = '7day'
        MONTH = '1month'
        QUARTER = '3month'
        HALFYEAR = '6month'
        YEAR = '12month'

    def __init__(self, username, api_key):
        self.api_key = api_key
        
        self.username = username
        self.rsession = requests.Session()
        self.retry_counter = 0

    def net_call(self,
                 http_method: str,
                 method: str,
                 params: dict = None,
                 data: dict = None,
                 json: dict = None,
                 headers: dict = None) -> dict:

        http_method = http_method.strip().upper()

        response = self.rsession.request(method=http_method,
                                         url='http://ws.audioscrobbler.com/2.0/',
                                         headers=headers,
                                         params=params,
                                         json=json,
                                         data=data)
        resp = response.json()

        if 200 <= response.status_code < 300:
            logger.debug(f'{http_method} {method} {response.status_code}')
            return resp

        code = resp.get('error', None)
        message = resp.get('message', None)

        if code:
            if code in [8, 11, 16]:
                if self.retry_counter < 5:
                    self.retry_counter += 1
                    logger.warning(f'{method} {response.status_code} {code} {message} retyring')
                    return self.net_call(http_method=http_method,
                                         method=method,
                                         params=params,
                                         data=data,
                                         json=json,
                                         headers=headers)
                else:
                    self.retry_counter = 0

        logger.error(f'{method} {response.status_code} {code} {message} retry limit reached')
        raise LastFMNetworkException(http_code=response.status_code, error_code=code, message=message)

    def get_request(self,
                    method: str,
                    params: dict = None,
                    **kwargs) -> dict:
       
        data = {
                "format": 'json',
                "method": method,
                "api_key": self.api_key,
                }
        if params is not None:
            data.update(params)
        if kwargs is not None:
            data.update({i: j for i, j in kwargs.items() if j is not None})

        return self.net_call(http_method='GET', method=method, params=data)

    def get_user_scrobble_count(self, username: str = None) -> int:
        if username is None:
            username = self.username
        logger.info(f'getting scrobble count {username}')
        return int(
            self.get_request(method='user.getinfo', user=username)
                .get('user', {})
                .get('playcount', None)
        )

    def get_recent_tracks(self,
                          username: str = None,
                          limit: int = None,
                          from_time: datetime = None,
                          to_time: datetime = None,
                          page_limit: int = 50) -> Optional[List[Scrobble]]:
        if limit is not None:
            logger.info(f'pulling {limit} tracks')
        else:
            logger.info(f'pulling all tracks')

        params = {
            'user': username or self.username
        }

        if from_time is not None:
            params['from'] = int(from_time.timestamp())
        if to_time is not None:
            params['to'] = int(to_time.timestamp())

        iterator = PageCollection(net=self, method='user.getrecenttracks', params=params, response_limit=limit, page_limit=page_limit)
        iterator.response_limit = limit + 1 if limit is not None else None
        iterator.load()

        items = iterator.items

        if len(items) >= 1:
            if items[0].get('@attr', {}).get('nowplaying', None):
                items.pop(0)

        return [self.parse_scrobble(i) for i in items[:limit]]

    def get_scrobbles_from_date(self,
                                input_date: date,
                                username: str = None,
                                limit: int = None) -> Optional[List[Scrobble]]:
        logger.info(f'getting {input_date} scrobbles for {username or self.username}')
        midnight = time(hour=0, minute=0, second=0)

        from_date = datetime.combine(date=input_date, time=midnight)
        to_date = datetime.combine(date=input_date + timedelta(days=1), time=midnight)

        return self.get_recent_tracks(username=username, from_time=from_date, to_time=to_date, limit=limit)

    def get_scrobble_count_from_date(self,
                                     input_date: date,
                                     username: str = None,
                                     limit: int = None) -> int:
        logger.info(f'getting {input_date} scrobble count for {username or self.username}')

        scrobbles = self.get_scrobbles_from_date(input_date=input_date, username=username, limit=limit)

        if scrobbles:
            return len(scrobbles)
        else:
            return 0

    def get_track(self,
                  name: str,
                  artist: str,
                  username: str = None) -> Optional[Track]:
        logger.info(f'getting {name} / {artist} for {username or self.username}')

        resp = self.get_request('track.getInfo',
                                track=name,
                                artist=artist,
                                user=username or self.username)

        if resp.get('track'):
            return self.parse_track(resp['track'])
        else:
            logging.error(f'abnormal response - {resp}')

    def get_album(self,
                  name: str,
                  artist: str,
                  username: str = None) -> Optional[Album]:
        logger.info(f'getting {name} / {artist} for {username or self.username}')

        resp = self.get_request('album.getInfo',
                                album=name,
                                artist=artist,
                                user=username or self.username)

        if resp.get('album'):
            return self.parse_album(resp['album'])
        else:
            logging.error(f'abnormal response - {resp}')

    def get_artist(self,
                   name: str,
                   username: str = None) -> Optional[Artist]:
        logger.info(f'getting {name} for {username or self.username}')

        resp = self.get_request('artist.getInfo',
                                artist=name,
                                user=username or self.username)

        if resp.get('artist'):
            return self.parse_artist(resp['artist'])
        else:
            logging.error(f'abnormal response - {resp}')

    def get_top_tracks(self,
                       period: Range,
                       username: str = None,
                       limit: int = None):
        if limit is not None:
            logger.info(f'pulling top {limit} tracks from {period.value} for {username or self.username}')
        else:
            logger.info(f'pulling top tracks from {period.value} for {username or self.username}')

        params = {
            'user': username or self.username,
            'period': period.value
        }

        iterator = PageCollection(net=self, method='user.gettoptracks', params=params, response_limit=limit)
        iterator.load()

        return [self.parse_track(i) for i in iterator.items]

    def get_top_albums(self,
                       period: Range,
                       username: str = None,
                       limit: int = None):
        if limit is not None:
            logger.info(f'pulling top {limit} albums from {period.value} for {username or self.username}')
        else:
            logger.info(f'pulling top albums from {period.value} for {username or self.username}')

        params = {
            'user': username or self.username,
            'period': period.value
        }

        iterator = PageCollection(net=self, method='user.gettopalbums', params=params, response_limit=limit)
        iterator.load()

        return [self.parse_chart_album(i) for i in iterator.items]

    def get_top_artists(self,
                        period: Range,
                        username: str = None,
                        limit: int = None):
        if limit is not None:
            logger.info(f'pulling top {limit} artists from {period.value} for {username or self.username}')
        else:
            logger.info(f'pulling top artists from {period.value} for {username or self.username}')

        params = {
            'user': username or self.username,
            'period': period.value
        }

        iterator = PageCollection(net=self, method='user.gettopartists', params=params, response_limit=limit)
        iterator.load()

        return [self.parse_artist(i) for i in iterator.items]

    def download_image_by_size(self, fm_object: Union[Track, Album, Artist], size: Image.Size):
        try:
            images = fm_object.images

            image_pointer = next((i for i in images if i.size == size), None)
            if image_pointer is not None:
                return self.download_image(image_pointer=image_pointer)
            else:
                logger.error(f'image of size {size.name} not found')
                raise ImageSizeNotAvailableException
        except AttributeError:
            logger.error(f'{fm_object} has no images')

    def download_best_image(self, fm_object: Union[Track, Album, Artist], final_scale=None, add_count: bool = False):
        try:
            images = sorted(fm_object.images, key=lambda x: x.size.value, reverse=True)

            for image in images:

                downloaded = self.download_image(image_pointer=image)
                if downloaded is not None:

                    if final_scale is not None:
                        if downloaded.shape != final_scale:
                            downloaded = cv2.resize(downloaded, final_scale)

                    if add_count:
                        self.add_scrobble_count_to_image(downloaded, fm_object.user_scrobbles)

                    return downloaded
                else:
                    logger.error('null image returned, iterating')
        except AttributeError:
            logger.error(f'{fm_object} has no images')

    @staticmethod
    def add_scrobble_count_to_image(image, count: int):
        cv2.putText(image,
                    f'{count:,}',
                    (11, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 0),
                    2)
        cv2.putText(image,
                    f'{count:,}',
                    (11, 38),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 0),
                    2)
        cv2.putText(image,
                    f'{count:,}',
                    (9, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 255),
                    2)

    @staticmethod
    def download_image(image_pointer: Image, cache=True):
        logger.info(f'downloading {image_pointer.size.name} image - {image_pointer.link}')
        if image_pointer.link is None or len(image_pointer.link) == 0 or image_pointer.link == '':
            logger.error('invalid image url')
            return None

        url_split = image_pointer.link.split('/')
        cache_path = os.path.join(config_directory, 'cache')
        file_path = os.path.join(cache_path, url_split[-2]+url_split[-1])

        if os.path.exists(file_path):
            return cv2.imread(file_path)

        resp = requests.get(image_pointer.link, stream=True)

        if 200 <= resp.status_code < 300:
            image = np.asarray(bytearray(resp.content), dtype="uint8")
            image = cv2.imdecode(image, cv2.IMREAD_COLOR)
            if cache:
                if not os.path.exists(cache_path):
                    os.makedirs(cache_path)
                if not cv2.imwrite(filename=file_path, img=image):
                    logger.error('failed to dump to cache')
            return image
        else:
            logger.error(f'http error {resp.status_code}')

    def get_weekly_charts(self, username: str = None):
        logger.info('getting weekly chart list')

        resp = self.get_request('user.getweeklychartlist', user=username or self.username)
        if resp:
            return [WeeklyChart(from_time=int(i['from']), to_time=int(i['to']))
                    for i in resp.get('weeklychartlist', {}).get('chart', [])]
        else:
            logger.error('no response')

    def get_weekly_chart(self,
                         object_type,
                         chart: WeeklyChart = None,
                         from_time: int = None,
                         to_time: int = None,
                         username: str = None,
                         limit: int = None):

        if object_type not in ['album', 'artist', 'track']:
            raise ValueError('invalid object type')

        if chart is None and (from_time is None or to_time is None):
            raise ValueError('no time range')

        if chart is not None:
            from_time = chart.from_secs
            to_time = chart.to_secs

        if limit is not None:
            logger.info(f'pulling top {limit} {object_type}s from {chart.from_date} to {chart.to_date} '
                        f'for {username or self.username}')
        else:
            logger.info(f'pulling top {object_type}s from {chart.from_date} to {chart.to_date} '
                        f'for {username or self.username}')

        params = {
            'user': username or self.username,
            'from': from_time,
            'to': to_time
        }

        resp = self.get_request(method=f'user.getweekly{object_type}chart', params=params)

        if resp:
            if object_type == 'track':
                return [self.parse_track(i) for i in resp.get('weeklytrackchart', {}).get('track', [])]
            elif object_type == 'album':
                return [self.parse_album(i) for i in resp.get('weeklyalbumchart', {}).get('album', [])]
            elif object_type == 'artist':
                return [self.parse_artist(i) for i in resp.get('weeklyartistchart', {}).get('artist', [])]
        else:
            logger.error('no response')

    @staticmethod
    def parse_wiki(wiki_dict) -> Optional[Wiki]:
        if wiki_dict:
            return Wiki(published=datetime.strptime(wiki_dict.get('published', None), '%d %b %Y, %H:%M'),
                        summary=wiki_dict.get('summary', None),
                        content=wiki_dict.get('content', None))
        else:
            return None

    def parse_artist(self, artist_dict) -> Artist:
        return Artist(name=artist_dict.get('name', 'n/a'),
                      url=artist_dict.get('url', None),
                      mbid=artist_dict.get('mbid', None),
                      listeners=int(artist_dict.get('stats', {}).get('listeners', 0)),
                      play_count=int(artist_dict.get('stats', {}).get('playcount', 0)),
                      user_scrobbles=int(artist_dict.get('stats', {}).get('userplaycount',
                                                                          artist_dict.get('playcount', 0))),
                      wiki=self.parse_wiki(artist_dict['wiki']) if artist_dict.get('wiki', None) else None,
                      images=[self.parse_image(i) for i in artist_dict.get('image', [])])

    def parse_album(self, album_dict) -> Album:
        return Album(name=album_dict.get('name', album_dict.get('title', 'n/a')),
                     url=album_dict.get('url', 'n/a'),
                     mbid=album_dict.get('mbid', 'n/a'),
                     listeners=int(album_dict.get('listeners', 0)),
                     play_count=int(album_dict.get('playcount', 0)),
                     user_scrobbles=int(album_dict.get('userplaycount', 0)),
                     wiki=self.parse_wiki(album_dict['wiki']) if album_dict.get('wiki', None) else None,
                     artist=album_dict.get('artist'),
                     images=[self.parse_image(i) for i in album_dict.get('image', [])])

    def parse_chart_album(self, album_dict) -> Album:
        return Album(name=album_dict.get('name', album_dict.get('title', 'n/a')),
                     url=album_dict.get('url', 'n/a'),
                     mbid=album_dict.get('mbid', 'n/a'),
                     listeners=int(album_dict.get('listeners', 0)),
                     user_scrobbles=int(album_dict.get('playcount', 0)),
                     wiki=self.parse_wiki(album_dict['wiki']) if album_dict.get('wiki', None) else None,
                     artist=album_dict.get('artist'),
                     images=[self.parse_image(i) for i in album_dict.get('image', [])])

    def parse_track(self, track_dict) -> Track:
        track = Track(name=track_dict.get('name', 'n/a'),
                      url=track_dict.get('url', 'n/a'),
                      mbid=track_dict.get('mbid', 'n/a'),
                      listeners=int(track_dict.get('listeners', 0)),
                      play_count=int(track_dict.get('playcount', 0)),
                      user_scrobbles=int(track_dict.get('userplaycount', 0)),
                      wiki=self.parse_wiki(track_dict['wiki']) if track_dict.get('wiki', None) else None,
                      images=[self.parse_image(i) for i in track_dict.get('image', [])])

        if track_dict.get('album', None):
            track.album = self.parse_album(track_dict['album'])

        if track_dict.get('artist', None):
            track.artist = self.parse_artist(track_dict['artist'])

        return track

    @staticmethod
    def parse_image(image_dict) -> Image:
        try:
            return Image(size=Image.Size[image_dict['size']], link=image_dict['#text'])
        except KeyError:
            return Image(size=Image.Size['other'], link=image_dict['#text'])

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
                if len(page) == 0 or self.counter > page.total_pages:
                    tracker = False
                else:
                    self.pages.append(page)
        else:
            tracker = True
            while tracker:
                page = self.iterate()
                if len(page) == 0 or self.counter > page.total_pages:
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
        attr = first_value['@attr']

        del first_value['@attr']
        items = list(first_value.values())[0]

        return Page(
            number=int(attr.get('page', None)),
            size=int(attr.get('perPage', None)),
            total=int(attr.get('total', None)),
            total_pages=int(attr.get('totalPages', None)),
            items=items)


@dataclass
class Page:
    number: int
    size: int
    total: int
    total_pages: int
    items: list

    def __len__(self):
        return len(self.items)
