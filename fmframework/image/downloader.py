import logging
import os
from typing import Union

import requests
import cv2
import numpy as np

from fmframework.model import Album, Artist, Image, Track
from fmframework import config_directory

logger = logging.getLogger(__name__)


class ImageSizeNotAvailableException(Exception):
    pass


class Downloader:
    def __init__(self):
        self.rsession = requests.Session()
        self.cache_path = os.path.join(config_directory, 'cache')

    def image_by_size(self,
                      fm_object: Union[Track, Album, Artist],
                      size: Image.Size,
                      check_cache=True,
                      cache=True):
        try:
            images = fm_object.images

            image_pointer = next((i for i in images if i.size == size), None)
            if image_pointer is not None:
                return self.download(image_pointer=image_pointer, check_cache=check_cache, cache=cache)
            else:
                logger.error(f'image of size {size.name} not found')
                raise ImageSizeNotAvailableException

        except AttributeError:
            logger.error(f'{fm_object} has no images')

    def best_image(self,
                   fm_object: Union[Track, Album, Artist],
                   final_scale=None,
                   check_cache=True,
                   cache=True):
        try:
            images = sorted(fm_object.images, key=lambda x: x.size.value, reverse=True)

            for image in images:

                downloaded = self.download(image_pointer=image, check_cache=check_cache, cache=cache)
                if downloaded is not None:

                    if final_scale is not None:
                        if downloaded.shape != final_scale:
                            downloaded = cv2.resize(downloaded, final_scale)

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
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (0, 0, 0),
                    2)
        cv2.putText(image,
                    f'{count:,}',
                    (11, 38),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (0, 0, 0),
                    2)
        cv2.putText(image,
                    f'{count:,}',
                    (9, 35),
                    cv2.FONT_HERSHEY_DUPLEX,
                    1,
                    (255, 255, 255),
                    2)

    def download(self, image_pointer: Image, check_cache=True, cache=True):
        """Perform network action to download Image object"""

        logger.info(f'downloading {image_pointer.size.name} image - {image_pointer.link}')

        # Check for valid link to download
        if image_pointer.link is None or len(image_pointer.link) == 0 or image_pointer.link == '':
            logger.error('invalid image url')
            return None

        url_split = image_pointer.link.split('/')
        file_path = os.path.join(self.cache_path, url_split[-2] + url_split[-1])

        if check_cache and os.path.exists(file_path):
            return cv2.imread(file_path)

        resp = self.rsession.get(image_pointer.link, stream=True)

        if 200 <= resp.status_code < 300:
            image = np.asarray(bytearray(resp.content), dtype="uint8")
            image = cv2.imdecode(image, cv2.IMREAD_COLOR)

            if image.any() and cache:
                if not os.path.exists(self.cache_path):
                    os.makedirs(self.cache_path)
                if not cv2.imwrite(filename=file_path, img=image):
                    logger.error('failed to dump to cache')

            return image
        else:
            logger.error(f'http error {resp.status_code}')
