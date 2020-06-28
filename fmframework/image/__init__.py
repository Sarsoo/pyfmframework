import numpy as np
from typing import List
from fmframework.net.network import Network, ImageSizeNotAvailableException
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


def get_image_grid_from_objects(net: Network, objects, image_size=None, final_scale=(300, 300), image_width: int = 5):
    logger.debug(f'getting {image_size.name if image_size is not None else "best"} image grid of {len(objects)} objects at width {image_width}')
    images = []
    for counter, iter_object in enumerate(objects):
        logger.debug(f'downloading image {counter+1} of {len(objects)}')
        try:
            if image_size is None:
                downloaded = net.download_best_image(iter_object, final_scale=final_scale)
            else:
                downloaded = net.download_image_by_size(iter_object, size=image_size)

            if downloaded is not None:
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


def generate_album_chart_grid(net: Network,
                              chart_range: Network.Range,
                              image_size: Image.Size = None,
                              limit: int = 20,
                              image_width: int = 5):
    chart = net.get_top_albums(period=chart_range, limit=limit)
    return get_image_grid_from_objects(net=net, objects=chart, image_size=image_size, image_width=image_width)
