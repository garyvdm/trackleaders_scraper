#!/usr/bin/env python

import json
import os
import logging
import re
import itertools
import collections
import json

import slimit
import slimit.visitors.nodevisitor
import slimit.ast
import dateutil.parser
import pytz
import aniso8601

import trackleaders_scraper.common as common


recived_at_re = re.compile('received at: (.*?) <br />')


def datetime_parse_localized_to_utc(localalize_str):
    dt_parse_tzinfos = {
        "BST": 3600
    }
    brackets_removed = localalize_str.replace('(', '').replace(')', '')
    try:
        localized = dateutil.parser.parse(brackets_removed, tzinfos=dt_parse_tzinfos)
    except ValueError as e:
        raise ValueError('{}: {}'.format(str(e), brackets_removed))
    return localized.astimezone(pytz.utc)

Point = collections.namedtuple('Point', ['timestamp', 'lat', 'lng'])

raw_to_point = lambda obj: Point(aniso8601.parse_datetime(obj['timestamp']), obj['lat'], obj['lng'])
point_to_raw = lambda point: {'timestamp': point.timestamp.isoformat(), 'lat': point.lat, 'lng': point.lng}


def parse_points_from_spotjs_text(js_text):
    spot_js = slimit.parser.Parser().parse(js_text)
    location = None
    for node in slimit.visitors.nodevisitor.visit(spot_js):
        if isinstance(node, slimit.ast.Assign):
            children = node.children()
            idnt = children[0].to_ecma()
            if idnt == 'point':
                for subnode in slimit.visitors.nodevisitor.visit(node):
                    if isinstance(subnode, list):
                        location = tuple((float(item.to_ecma()) for item in subnode))
        if isinstance(node, slimit.ast.FunctionCall):
            children = node.children()
            idnt = children[0].to_ecma()
            if idnt == 'infowindow.setContent':
                recived_at_m = recived_at_re.search(children[1].to_ecma())
                recived_at_utc = datetime_parse_localized_to_utc(recived_at_m.group(1))
                yield Point(recived_at_utc, location[0], location[1])


def main():
    args = common.get_base_argparser().parse_args()
    common.configure_logging(args)

    race_path = common.get_race_path(args.race)

    with open(os.path.join(race_path, 'riders.json')) as f:
        riders = json.load(f)

    session = common.get_trackleaders_session()

    for rider in riders:
        try:
            logging.info('Getting data for {name}'.format(**rider))
            rider_path = os.path.join(race_path, rider['url_fragment'])

            rider_points_path = os.path.join(rider_path, 'points.json')
            if os.path.exists(rider_points_path):
                with open(rider_points_path) as f:
                    oldpoints = json.load(f)
            else:
                oldpoints = []
            oldpoints = [raw_to_point(point) for point in oldpoints]

            spot_js_url = 'http://trackleaders.com/spot/{}/{}.js'.format(args.race, rider['url_fragment'])
            spot_js_response = session.get(spot_js_url)
            spot_js_response.raise_for_status()
            newpoints = parse_points_from_spotjs_text(spot_js_response.text)

            points_set = set(itertools.chain(oldpoints, newpoints))
            points_sorted = [point_to_raw(point) for point in sorted(points_set)]
            with common.DelayedKeyboardInterrupt():
                if not os.path.exists(rider_path):
                    os.mkdir(rider_path)
                with open(rider_points_path, 'w') as f:
                    json.dump(points_sorted, f, indent=2)

        except Exception:
            logging.exception('Error for {name}'.format(**rider))

