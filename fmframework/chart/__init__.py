from bs4 import BeautifulSoup
import requests
from datetime import date

from fmframework.model.album import Album
from fmframework.model.artist import Artist
from fmframework.model.fm import Image
from fmframework.net.network import Network
import fmframework.image

import logging

logger = logging.getLogger(__name__)


def get_album_chart_image(net: Network,
                          username: str,
                          from_date: date,
                          to_date: date,
                          limit: int = 20,
                          image_size: Image.Size = None,
                          image_width: int = 5):
    album_chart = get_populated_album_chart(net=net, username=username,
                                            from_date=from_date, to_date=to_date,
                                            limit=limit)
    return fmframework.image.get_image_grid_from_objects(net=net,
                                                         objects=album_chart,
                                                         image_size=image_size,
                                                         image_width=image_width)


def get_populated_album_chart(net: Network, username: str, from_date: date, to_date: date, limit: int):
    chart = get_scraped_album_chart(username, from_date, to_date, limit)
    logger.info('populating scraped albums')
    albums = []
    for counter, scraped in enumerate(chart):
        logger.debug(f'populating {counter+1} of {len(chart)}')
        albums.append(net.get_album(name=scraped.name, artist=scraped.artist.name))

    return albums


def get_scraped_album_chart(username: str, from_date: date, to_date: date, limit: int):
    logger.info(f'scraping album chart from {from_date} to {to_date} for {username}')

    pages = int(limit / 50)
    if limit % 50 != 0:
        pages += 1

    albums = []
    for i in range(pages):
        scraped_albums = get_scraped_album_chart_page(username, from_date, to_date, i + 1)
        if scraped_albums is not None:
            albums += scraped_albums

    return albums[:limit]


def get_scraped_album_chart_page(username: str, from_date: date, to_date: date, page: int):
    logger.debug(f'loading page {page} from {from_date} to {to_date} for {username}')

    html = requests.get(f'https://www.last.fm/user/{username}/library/albums'
                        f'?from={from_date.strftime("%Y-%m-%d")}'
                        f'&to={to_date.strftime("%Y-%m-%d")}'
                        f'&page={page}')
    if 200 <= html.status_code < 300:
        parser = BeautifulSoup(html.content, 'html.parser')

        chart_section = parser.find('section', id='top-albums-section')

        rows = chart_section.find_all('tr', 'chartlist-row')

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

            artist = Artist(name=artist_name)
            album = Album(name=album_name, artist=artist, user_scrobbles=scrobble_count)
            albums.append(album)

        return albums
    else:
        logger.error(f'HTTP error occurred {html.status_code}')
