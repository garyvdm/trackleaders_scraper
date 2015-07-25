import argparse
import functools
import logging
import os
import signal
import collections
import json
import sys

import requests
import aniso8601
import geographiclib.geodesic

geodesic = geographiclib.geodesic.Geodesic.WGS84

def get_base_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('race', help='Race url fragment.')
    return parser


def configure_logging(args):
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("requests.packages.urllib3").setLevel(logging.WARN)


def get_trackleaders_session():
    trackleaders_session = requests.Session()
    trackleaders_session.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0'
    return trackleaders_session


get_race_path = functools.partial(os.path.join, 'races')
get_riders_path = lambda race_path: os.path.join(race_path, 'riders.json')


class DelayedKeyboardInterrupt(object):
    def __enter__(self):
        self.signal_received = False
        self.old_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self.handler)

    def handler(self, signal, frame):
        self.signal_received = (signal, frame)
        logging.debug('SIGINT received. Delaying KeyboardInterrupt.')

    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)
        if self.signal_received:
            self.old_handler(*self.signal_received)

def retry(func, retry_count=3):
    try_count = 0
    errors = []
    while try_count < retry_count:
        try:
            return func()
        except Exception:
            errors.append(sys.exc_info())
    raise Exception("Failed {} times.".format(try_count), errors=errors)


Point = collections.namedtuple('Point', ['timestamp', 'lat', 'lng'])

raw_to_point = lambda obj: Point(aniso8601.parse_datetime(obj['timestamp']), obj['lat'], obj['lng'])
point_to_raw = lambda point: {'timestamp': point.timestamp.isoformat(), 'lat': point.lat, 'lng': point.lng}


def load_rider_points(rider_points_path=None, rider_path=None):
    if rider_points_path is None:
        rider_points_path = os.path.join(rider_path, 'points.json')
    if os.path.exists(rider_points_path):
        with open(rider_points_path) as f:
            points = json.load(f)
    else:
        points = []
    return [raw_to_point(point) for point in points]

functools.lru_cache(1)
def get_google_api_key():
    with open('google-api-key') as f:
        return f.read().strip()
