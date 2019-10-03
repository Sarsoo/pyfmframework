from fmframework.io.csv import export_scrobbles
from fmframework.net.network import Network

import sys
import os
import logging

logger = logging.getLogger('fmframework')

log_format = '%(asctime)s %(levelname)s %(name)s - %(funcName)s - %(message)s'

file_handler = logging.FileHandler(".fm/backup.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

stream_log_format = '%(levelname)s %(name)s:%(funcName)s - %(message)s'
stream_formatter = logging.Formatter(stream_log_format)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_formatter)

logger.addHandler(stream_handler)


def backup_scrobbles(file_path):
    net = Network(username='sarsoo', api_key=os.environ['FMKEY'])

    scrobbles = net.get_recent_tracks()
    
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    export_scrobbles(scrobbles, file_path)


if __name__ == '__main__':
    backup_scrobbles(sys.argv[1])
