from datetime import date, datetime, timedelta
from typing import Union

from bs4 import BeautifulSoup
from requests import Session
from urllib import parse

from fmframework.model import Track, Artist, Album, Scrobble
from fmframework.net.network import Network, LastFMNetworkException

import logging

logger = logging.getLogger(__name__)


class LibraryScraper:
    rsession = Session()

    @staticmethod
    def api_date_range_to_url_string(period: Network.Range):
        if period == Network.Range.WEEK:
            return 'LAST_7_DAYS'
        elif period == Network.Range.MONTH:
            return 'LAST_30_DAYS'
        elif period == Network.Range.QUARTER:
            return 'LAST_90_DAYS'
        elif period == Network.Range.HALFYEAR:
            return 'LAST_180_DAYS'
        elif period == Network.Range.YEAR:
            return 'LAST_365_DAYS'
        elif period == Network.Range.OVERALL:
            return 'ALL'
        else:
            raise TypeError(f'invalid period provided, {period} / {type(period)}')

    @staticmethod
    def artist_scrobbles(username: str, artist: str, net: Network = None, whole_track=True,
                         from_date: datetime = None, to_date: datetime = None,
                         date_preset: str = None, reverse: bool = False):
        logger.info(f"loading {artist}'s tracks for {username}")

        artists_tracks = LibraryScraper.artist_tracks(username=username, artist=artist, net=net,
                                                      whole_track=False, from_date=from_date, to_date=to_date,
                                                      date_preset=date_preset)

        scrobbles = []
        for track in artists_tracks:
            tracks_scrobbles = LibraryScraper.track_scrobbles(username=username, artist=artist, track=track.name,
                                                              net=net, whole_track=whole_track,
                                                              from_date=from_date, to_date=to_date,
                                                              date_preset=date_preset)

            if tracks_scrobbles is not None:
                scrobbles += tracks_scrobbles
            else:
                logger.warning(f'no scrobbles returned for {track.name} / {track.artist.name} / {username}')

        return sorted(scrobbles, key=lambda x: x.time, reverse=reverse)

    @staticmethod
    def artist_tracks(username: str, artist: str, net: Network = None, whole_track=True,
                      from_date: datetime = None, to_date: datetime = None,
                      date_preset: str = None):
        logger.info(f"loading {artist}'s tracks for {username}")

        tracks = LibraryScraper.scraped_artist_tracks(username=username, artist=artist,
                                                      from_date=from_date, to_date=to_date,
                                                      date_preset=date_preset)

        if whole_track and net is None:
            raise NameError('Network required for populating tracks')

        populated_tracks = []
        if tracks is not None:
            if whole_track:
                for track in tracks:
                    populated_tracks.append(net.track(name=track.name, artist=track.artist.name, username=username))

                return populated_tracks
            else:
                return tracks
        else:
            logger.error(f'no scraped tracks returned for {artist} / {username}')

    @staticmethod
    def scraped_artist_tracks(username: str, artist: str,
                              from_date: datetime = None, to_date: datetime = None,
                              date_preset: str = None):
        logger.info(f'loading page scraped {artist} tracks for {username}')

        page1 = LibraryScraper.scraped_artist_subpage(username=username, artist=artist, page=1,
                                                      url_key='tracks', include_pages=True,
                                                      from_date=from_date, to_date=to_date,
                                                      date_preset=date_preset)

        if page1 is not None:
            tracks = page1[0]
            for page_number in range(page1[1] - 1):

                page = LibraryScraper.scraped_artist_subpage(username=username, artist=artist,
                                                             url_key='tracks',
                                                             page=page_number + 2,
                                                             from_date=from_date, to_date=to_date,
                                                             date_preset=date_preset)

                if page is not None:
                    tracks += page
                else:
                    logger.error(f'no tracks returned for {artist} / {username}')

            track_objects = []
            for album in tracks:
                name_cell = album.find('td', class_='chartlist-name').find('a')
                count_cell = album.find(class_='chartlist-count-bar-value')

                track_objects.append(Track(name=name_cell.string,
                                           artist=Artist(name=artist),
                                           url=name_cell['href'],
                                           user_scrobbles=int(count_cell.contents[0].strip())))

            return track_objects
        else:
            logger.error(f'no tracks returned for page 1 of {artist} / {username}')

    @staticmethod
    def artists_albums(username: str, artist: str, net: Network = None, whole_album=True,
                       from_date: datetime = None, to_date: datetime = None,
                       date_preset: str = None):
        logger.info(f"loading {artist}'s albums for {username}")

        albums = LibraryScraper.scraped_artists_albums(username=username, artist=artist,
                                                       from_date=from_date, to_date=to_date,
                                                       date_preset=date_preset)

        if whole_album and net is None:
            raise NameError('Network required for populating albums')

        populated_albums = []
        if albums is not None:
            if whole_album:
                for album in albums:
                    populated_albums.append(net.album(name=album.name, artist=album.artist.name, username=username))

                return populated_albums
            else:
                return albums
        else:
            logger.error(f'no scraped albums returned for {artist} / {username}')

    @staticmethod
    def scraped_artists_albums(username: str, artist: str,
                               from_date: datetime = None, to_date: datetime = None,
                               date_preset: str = None):
        logger.info(f'loading page scraped {artist} albums for {username}')

        page1 = LibraryScraper.scraped_artist_subpage(username=username, artist=artist, page=1,
                                                      url_key='albums',
                                                      include_pages=True,
                                                      from_date=from_date, to_date=to_date,
                                                      date_preset=date_preset)

        if page1 is not None:
            albums = page1[0]
            for page_number in range(page1[1] - 1):

                page = LibraryScraper.scraped_artist_subpage(username=username, artist=artist,
                                                             url_key='albums',
                                                             page=page_number + 2,
                                                             from_date=from_date, to_date=to_date,
                                                             date_preset=date_preset)

                if page is not None:
                    albums += page
                else:
                    logger.error(f'no albums returned for {artist} / {username}')

            albums_objects = []
            for album in albums:
                name_cell = album.find('td', class_='chartlist-name').find('a')
                count_cell = album.find(class_='chartlist-count-bar-value')

                albums_objects.append(Album(name=name_cell.string,
                                            artist=Artist(name=artist),
                                            user_scrobbles=int(count_cell.contents[0].strip()),
                                            url=name_cell['href']))

            return albums_objects
        else:
            logger.error(f'no albums returned for page 1 of {artist} / {username}')

    @staticmethod
    def album_scrobbles(username: str, artist: str, album: str, net: Network = None, whole_track=True,
                        from_date: datetime = None, to_date: datetime = None,
                        date_preset: str = None, reverse: bool = False):
        logger.info(f"loading {album} / {artist}'s tracks for {username}")

        albums_tracks = LibraryScraper.album_tracks(username=username, artist=artist, album=album, net=net,
                                                    whole_track=False, from_date=from_date, to_date=to_date,
                                                    date_preset=date_preset)

        if albums_tracks is None:
            logger.error(f'no tracks returned for {album} / {artist} / {username}')
            return

        scrobbles = []
        for track in albums_tracks:
            tracks_scrobbles = LibraryScraper.track_scrobbles(username=username, artist=artist, track=track.name,
                                                              net=net, whole_track=whole_track,
                                                              from_date=from_date, to_date=to_date,
                                                              date_preset=date_preset)

            if tracks_scrobbles is not None:
                scrobbles += tracks_scrobbles
            else:
                logger.warning(f'no scrobbles returned for {track.name} / {track.artist.name} / {username}')

        return sorted(scrobbles, key=lambda x: x.time, reverse=reverse)

    @staticmethod
    def album_tracks(username: str, artist: str, album: str, net: Network = None, whole_track=True,
                     from_date: datetime = None, to_date: datetime = None,
                     date_preset: str = None):
        logger.info(f"loading {artist}'s {album} tracks for {username}")

        tracks = LibraryScraper.scraped_album_tracks(username=username, artist=artist, album=album,
                                                     from_date=from_date, to_date=to_date,
                                                     date_preset=date_preset)

        if whole_track and net is None:
            raise NameError('Network required for populating tracks')

        populated_tracks = []
        if tracks is not None:
            if whole_track:
                for track in tracks:
                    populated_tracks.append(net.track(name=track.name, artist=track.artist.name, username=username))

                return populated_tracks
            else:
                return tracks
        else:
            logger.error(f'no scraped tracks returned for {album} / {artist} / {username}')

    @staticmethod
    def scraped_album_tracks(username: str, artist: str, album: str,
                             from_date: datetime = None, to_date: datetime = None,
                             date_preset: str = None):
        logger.info(f'loading page scraped {artist} albums for {username}')

        page1 = LibraryScraper.scraped_artist_subpage(username=username, artist=artist, page=1,
                                                      album=album,
                                                      include_pages=True,
                                                      from_date=from_date, to_date=to_date,
                                                      date_preset=date_preset)

        if page1 is not None:
            albums = page1[0]
            for page_number in range(page1[1] - 1):

                page = LibraryScraper.scraped_artist_subpage(username=username, artist=artist,
                                                             album=album,
                                                             page=page_number + 2,
                                                             from_date=from_date, to_date=to_date,
                                                             date_preset=date_preset)

                if page is not None:
                    albums += page
                else:
                    logger.error(f'no tracks returned for {album} / {artist} / {username}')

            track_objects = []
            for album in albums:
                name_cell = album.find('td', class_='chartlist-name').find('a')
                count_cell = album.find(class_='chartlist-count-bar-value')

                artist_name = parse.unquote_plus(name_cell['href'].split('/')[2])

                track_objects.append(Track(name=name_cell.string,
                                           artist=Artist(name=artist_name),
                                           url=name_cell['href'],
                                           user_scrobbles=int(count_cell.contents[0].strip())))

            return track_objects
        else:
            logger.error(f'no tracks returned for page 1 of {album} / {artist} / {username}')

    # TODO cache pulled album to reduce requests
    @staticmethod
    def track_scrobbles(username: str, artist: str, track: str, net: Network = None, whole_track=True,
                        from_date: datetime = None, to_date: datetime = None,
                        date_preset: str = None):
        logger.info(f"loading {track} / {artist} for {username}")

        tracks = LibraryScraper.scraped_track_scrobbles(username=username, artist=artist, track=track,
                                                        from_date=from_date, to_date=to_date,
                                                        date_preset=date_preset)

        if whole_track and net is None:
            raise NameError('Network required for populating tracks')

        populated_scrobbles = []
        if tracks is not None:
            if whole_track:
                for scrobble in tracks:
                    pulled_scrobble = net.track(name=scrobble.track.name,
                                                artist=scrobble.track.artist.name,
                                                username=username)
                    pulled_scrobble.album = net.album(name=scrobble.track.album.name,
                                                      artist=scrobble.track.album.artist.name,
                                                      username=username)

                    scrobble.track = pulled_scrobble
                    populated_scrobbles.append(scrobble)

                return populated_scrobbles
            else:
                return tracks
        else:
            logger.error(f'no scraped tracks returned for {track} / {artist} / {username}')

    @staticmethod
    def scraped_track_scrobbles(username: str, artist: str, track: str,
                                from_date: datetime = None, to_date: datetime = None,
                                date_preset: str = None):
        logger.info(f'loading page scraped {track} / {artist} for {username}')

        page1 = LibraryScraper.scraped_artist_subpage(username=username, artist=artist, page=1,
                                                      track=track,
                                                      include_pages=True,
                                                      from_date=from_date, to_date=to_date,
                                                      date_preset=date_preset)

        if page1 is not None:
            albums = page1[0]
            for page_number in range(page1[1] - 1):

                page = LibraryScraper.scraped_artist_subpage(username=username, artist=artist,
                                                             track=track,
                                                             page=page_number + 2,
                                                             from_date=from_date, to_date=to_date,
                                                             date_preset=date_preset)

                if page is not None:
                    albums += page
                else:
                    logger.error(f'no scrobbles returned for {track} / {artist} / {username}')

            track_objects = []
            for album in albums:
                name_cell = album.find('td', class_='chartlist-name').find('a')
                album_cell = album.find('td', class_='chartlist-album').find('a')

                album_artist_name = parse.unquote_plus(album_cell['href'].split('/')[2])
                scrobble_timestamp = album.find('td', class_='chartlist-timestamp').find('span')

                timestamp_parts = [i.strip() for i in scrobble_timestamp.string.split(', ')]

                if len(timestamp_parts) == 1:
                    try:
                        scrobble_datetime = datetime.strptime(timestamp_parts[0], '%d %b %I:%M%p')  # this year
                        scrobble_datetime = scrobble_datetime.replace(year=date.today().year)
                    except ValueError:
                        scrobble_datetime = datetime.now() - timedelta(hours=int(timestamp_parts[0][0]))  # X hours ago
                elif len(timestamp_parts) == 2:
                    recombined = ' '.join(timestamp_parts)
                    scrobble_datetime = datetime.strptime(recombined, '%d %b %Y %I:%M%p')  # previous year
                else:
                    scrobble_datetime = None
                    logger.error(f'{len(timestamp_parts)} timestamp parts found, {timestamp_parts}')

                track_objects.append(Scrobble(track=Track(name=name_cell.string,
                                                          artist=Artist(name=artist),
                                                          album=Album(name=album_cell.string,
                                                                      artist=Artist(name=album_artist_name)),
                                                          url=name_cell['href']),
                                              time=scrobble_datetime)
                                     )

            length = len(track_objects)
            for scrobble in track_objects:
                scrobble.track.user_scrobbles = length

            return track_objects
        else:
            logger.error(f'no scrobbles returned for page 1 of {track} / {artist} / {username}')

    @staticmethod
    def scraped_artist_subpage(username: str, artist: str, page: int,

                               url_key: str = None,
                               album: str = None,
                               track: str = None,

                               include_pages=False,
                               from_date: datetime = None, to_date: datetime = None,
                               date_preset: Union[str, Network.Range] = None):
        logger.debug(f'loading page {page} of {artist} for {username}')

        url = f'https://www.last.fm/user/{username}/library/music/{parse.quote_plus(artist)}'

        if album:
            url += f'/{parse.quote_plus(album)}'
        elif track:
            url += f'/_/{parse.quote_plus(track)}'

        if url_key:
            url += f'/+{url_key}'

        url += f'?page={page}'

        if from_date and to_date:
            url += f'&from={from_date.strftime("%Y-%m-%d")}&to={to_date.strftime("%Y-%m-%d")}'
        elif date_preset:
            if isinstance(date_preset, str):
                date_preset = date_preset.strip().upper()
                if date_preset not in ['LAST_7_DAYS', 'LAST_30_DAYS', 'LAST_90_DAYS',
                                       'LAST_180_DAYS', 'LAST_365_DAYS', 'ALL']:
                    raise ValueError(f'date range {date_preset} not of allowed value')
                url += f'&date_preset={date_preset}'

            elif isinstance(date_preset, Network.Range):
                url += f'&date_preset={LibraryScraper.api_date_range_to_url_string(date_preset)}'

            else:
                raise TypeError(f'invalid period provided, {date_preset} / {type(date_preset)}')

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB,en;q=0.5",
            "DNT": "1",
            "Host": "www.last.fm",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0",
        }
        html = LibraryScraper.rsession.get(url, headers=headers)

        if 200 <= html.status_code < 300:
            parser = BeautifulSoup(html.content, 'html.parser')

            objs = [i for i in parser.find_all('tr') if i.find('td', class_='chartlist-name')]

            if include_pages:
                return objs, len(parser.find_all('li', class_='pagination-page'))
            else:
                return objs

        else:
            logger.error(f'HTTP error occurred {html.status_code}')


class UserScraper:
    rsession = Session()

    @staticmethod
    def album_chart(net: Network, username: str, from_date: date, to_date: date, limit: int):
        """Scrape chart from last.fm frontend before pulling each from the backend for a complete object"""

        chart = UserScraper.scraped_album_chart(username or net.username, from_date, to_date, limit)
        logger.info('populating scraped albums')
        albums = []
        for counter, scraped in enumerate(chart):
            logger.debug(f'populating {counter+1} of {len(chart)}')
            try:
                albums.append(net.album(name=scraped.name, artist=scraped.artist.name))
            except LastFMNetworkException:
                logger.exception(f'error occured during album retrieval')

        return albums

    @staticmethod
    def scraped_album_chart(username: str, from_date: date, to_date: date, limit: int):
        """Scrape 'light' objects from last.fm frontend based on date range and limit"""

        logger.info(f'scraping album chart from {from_date} to {to_date} for {username}')

        pages = int(limit / 50)
        if limit % 50 != 0:
            pages += 1

        albums = []
        for i in range(pages):
            scraped_albums = UserScraper.scraped_album_chart_page(username, from_date, to_date, i + 1)
            if scraped_albums is not None:
                albums += scraped_albums

        return albums[:limit]

    @staticmethod
    def scraped_album_chart_page(username: str, from_date: date, to_date: date, page: int):
        """Scrape 'light' objects single page of last.fm frontend based on date range"""

        logger.debug(f'loading page {page} from {from_date} to {to_date} for {username}')

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB,en;q=0.5",
            "DNT": "1",
            "Host": "www.last.fm",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0",
        }
        html = UserScraper.rsession.get(f'https://www.last.fm/user/{username}/library/albums'
                                        f'?from={from_date.strftime("%Y-%m-%d")}'
                                        f'&to={to_date.strftime("%Y-%m-%d")}'
                                        f'&page={page}',
                                        headers=headers)
        if 200 <= html.status_code < 300:
            parser = BeautifulSoup(html.content, 'html.parser')
            rows = parser.find_all('tr', 'chartlist-row')

            albums = []
            for row in rows:
                names = row.find_all('a', title=True)
                album_name = names[0]['title']
                artist_name = names[1]['title']

                scrobble_tag = row.find('span', {"class": "chartlist-count-bar-value"})
                scrobble_count = [int(s) for s in scrobble_tag.contents[0].split() if s.isdigit()]

                if len(scrobble_count) != 1:
                    logger.error('no scrobble count integers found')
                    scrobble_count = 0
                else:
                    scrobble_count = scrobble_count[0]

                album = Album(name=album_name,
                              artist=Artist(name=artist_name),
                              user_scrobbles=scrobble_count)
                albums.append(album)

            return albums
        else:
            logger.error(f'HTTP error occurred {html.status_code}')
