import numpy as np
from typing import List
from datetime import date

from fmframework.net.network import Network
from fmframework.chart import get_populated_album_chart
from fmframework.image.downloader import Downloader, ImageSizeNotAvailableException
from fmframework.model import Image

import logging
logger = logging.getLogger(__name__)


def get_blank_image(height, width):
    return np.zeros((height, width, 3), np.uint8)


def arrange_cover_grid(images: List[np.array], width: int = 5):
    logger.debug(f'arranging {len(images)} images at width {width}')
    rows = []
    for row in chunk(images, width):
        row_img = row[0]
        for image in row[1:]:
            row_img = np.concatenate((row_img, image), axis=1)

        # handle incomplete final row
        if len(row) < width and len(rows) > 0:
            width = rows[0].shape[1] - row_img.shape[1]
            height = rows[0].shape[0]
            logger.debug(rows[0].shape)
            row_img = np.concatenate((row_img, get_blank_image(width=width, height=height)), axis=1)

        rows.append(row_img)

    final_img = rows[0]
    if len(rows) > 1:
        for row in rows[1:]:
            final_img = np.concatenate((final_img, row), axis=0)
    return final_img


def get_image_grid_from_objects(objects,
                                image_size=None,
                                final_scale=(300, 300),
                                image_width: int = 5,
                                overlay_count: bool = False,
                                loader=None,
                                check_cache=True,
                                cache=True):
    logger.debug(f'getting {image_size.name if image_size is not None else "best"} image grid '
                 f'of {len(objects)} objects at width {image_width}')

    if loader is None:
        loader = Downloader()

    images = []
    for counter, iter_object in enumerate(objects):
        logger.debug(f'downloading image {counter+1} of {len(objects)}')
        try:
            if image_size is None:
                downloaded = loader.download_best_image(iter_object,
                                                        final_scale=final_scale,
                                                        check_cache=check_cache,
                                                        cache=cache)
            else:
                downloaded = loader.download_image_by_size(iter_object,
                                                           size=image_size,
                                                           check_cache=check_cache,
                                                           cache=cache)

            if downloaded is not None:
                if overlay_count:
                    loader.add_scrobble_count_to_image(downloaded, iter_object.user_scrobbles)

                images.append(downloaded)
            else:
                images.append(get_blank_image(final_scale[0], final_scale[1]))

        except ImageSizeNotAvailableException:
            logger.error(f'{image_size.name if image_size is not None else "best"} image not available for {iter_object.name}')

    grid_image = arrange_cover_grid(images=images, width=image_width)
    return grid_image


def chunk(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]


class AlbumChartCollage:

    @staticmethod
    def from_relative_range(net: Network,
                            chart_range: Network.Range,
                            username: str = None,
                            limit: int = 20,
                            overlay_count: bool = False,
                            image_size: Image.Size = None,
                            image_width: int = 5,
                            check_cache=True,
                            cache=True):
        chart = net.get_top_albums(username=username,
                                   period=chart_range,
                                   limit=limit)
        return get_image_grid_from_objects(objects=chart,
                                           image_size=image_size,
                                           image_width=image_width,
                                           overlay_count=overlay_count,
                                           check_cache=check_cache,
                                           cache=cache)

    @staticmethod
    def from_dates(net: Network,
                   from_date: date,
                   to_date: date,
                   username: str = None,
                   limit: int = 20,
                   overlay_count: bool = False,
                   image_size: Image.Size = None,
                   image_width: int = 5,
                   check_cache=True,
                   cache=True):
        chart = get_populated_album_chart(net=net,
                                          username=username,
                                          from_date=from_date,
                                          to_date=to_date,
                                          limit=limit)
        return get_image_grid_from_objects(objects=chart,
                                           image_size=image_size,
                                           image_width=image_width,
                                           overlay_count=overlay_count,
                                           check_cache=check_cache,
                                           cache=cache)
