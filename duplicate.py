from fmframework.net.network import Network, LastFMNetworkException

from urllib import parse
from csv import DictWriter
import os
import logging

username = 'sarsoo'

logger = logging.getLogger('fmframework')

directory = '.fm'

if not os.path.exists(directory):
    os.makedirs(directory)

file_handler = logging.FileHandler(f"{directory}/deduplicate.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(funcName)s - %(message)s'))
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(levelname)s %(name)s:%(funcName)s - %(message)s'))
logger.addHandler(stream_handler)


# chunk scrobbles into successive groups of sample size
def neighbouring_scrobbles(scrobbles, sample_size):

    if len(scrobbles) < sample_size:
        logger.warning(f'less scrobbles than provided sample size {len(scrobbles)}/{sample_size}')

    start_idx = 0
    final_idx = min(sample_size, len(scrobbles) - 1)

    while start_idx < len(scrobbles):
        yield scrobbles[start_idx:final_idx]
        start_idx += 1
        final_idx = min(final_idx + 1, len(scrobbles) - 1)


def check_for_duplicates(fmkey, retrieval_limit):
    net = Network(username=username, api_key=fmkey)
    net.retry_counter = 20

    try:
        scrobbles = net.recent_tracks(limit=retrieval_limit, page_limit=200)

        if not scrobbles:
            logger.error('No scrobbles returned')
            return

        duplicates_found = []
        for scrobble_group in neighbouring_scrobbles(scrobbles, 7):
            for idx, to_check in enumerate(scrobble_group[1:]):
                if scrobble_group[0].track == to_check.track:
                    duplicates_found.append((scrobble_group[0], to_check, idx + 1))

        print(f'Found {len(duplicates_found)} duplicates')
        print()

        for duplicate in duplicates_found:
            print(f'{duplicate[1].time} - {duplicate[0].time}, {duplicate[0].track}')
            print(f'https://www.last.fm/user/{username}/library/music/'
                  f'{parse.quote_plus(duplicate[0].track.artist.name)}/_/'
                  f'{parse.quote_plus(duplicate[0].track.name)}')
            print(f'https://www.last.fm/user/{username}/library'
                  f'?from={duplicate[0].time.strftime("%Y-%m-%d")}'
                  f'&to={duplicate[1].time.strftime("%Y-%m-%d")}')
            print()

        headers = ['initial', 'duplicate', 'scrobble difference', 'difference minutes', 'track',
                   'album', 'artist', 'track url', 'scrobbles url']
        with open('duplicates.csv', 'w', newline='', encoding='utf-16') as fileobj:

            writer = DictWriter(fileobj, fieldnames=headers)
            writer.writeheader()

            for duplicate in duplicates_found:
                writer.writerow({
                    'initial': duplicate[1].time,
                    'duplicate': duplicate[0].time,
                    'scrobble difference': duplicate[2],
                    'difference minutes': (duplicate[0].time - duplicate[1].time).total_seconds() / 60,
                    'track': duplicate[0].track.name,
                    'album': duplicate[0].track.album.name,
                    'artist': duplicate[0].track.artist.name,
                    'track url': f'https://www.last.fm/user/{username}/library/music/'
                                 f'{parse.quote_plus(duplicate[0].track.artist.name)}/_/'
                                 f'{parse.quote_plus(duplicate[0].track.name)}',
                    'scrobbles url': f'https://www.last.fm/user/{username}/library'
                                     f'?from={duplicate[1].time.strftime("%Y-%m-%d")}'
                                     f'&to={duplicate[0].time.strftime("%Y-%m-%d")}'
                })

    except LastFMNetworkException:
        logger.exception('error during scrobble retrieval')


if __name__ == '__main__':
    key = os.environ.get('FMKEY')
    if key is None:
        key = input('enter Last.fm key: ')

    limit = input('limit? (0 for none): ')

    if limit.isdigit():
        limit = int(limit)
        if limit == 0:
            limit = None
    else:
        print('not a number, setting to none')
        limit = None

    check_for_duplicates(key, limit)
    input('done, hit key to quit...')
