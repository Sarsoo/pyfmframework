from fmframework.io.csv import export_scrobbles
from fmframework.net.network import Network, LastFMNetworkException

import sys
import os
import logging

logger = logging.getLogger('fmframework')

file_handler = logging.FileHandler(".fm/backup.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(funcName)s - %(message)s'))
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(levelname)s %(name)s:%(funcName)s - %(message)s'))
logger.addHandler(stream_handler)


def backup_scrobbles(file_path):
    net = Network(username='sarsoo', api_key=os.environ['FMKEY'])

    try:
        scrobbles = net.get_recent_tracks()

        if not os.path.exists(file_path):
            os.makedirs(file_path)

        export_scrobbles(scrobbles, file_path)

    except LastFMNetworkException:
        logger.exception('error during scrobble retrieval')


if __name__ == '__main__':
    backup_scrobbles(sys.argv[1])
