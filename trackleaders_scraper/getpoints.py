#!/usr/bin/env python

import os
import logging
import re
import itertools
import json
import functools

import slimit
import slimit.visitors.nodevisitor
import slimit.ast
import dateutil.parser
import pytz

import trackleaders_scraper.common as common


recived_at_re = re.compile('received at: (.*?) <br />')


def datetime_parse_localized_to_utc(localalize_str):
    dt_parse_tzinfos = {
        "BST": 3600,
        "CET": 7200,
    }
    brackets_removed = localalize_str.replace('(', '').replace(')', '')
    try:
        localized = dateutil.parser.parse(brackets_removed, tzinfos=dt_parse_tzinfos)
    except ValueError as e:
        raise ValueError('{}: {}'.format(str(e), brackets_removed))
    return localized.astimezone(pytz.utc)



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
                yield common.Point(recived_at_utc, location[0], location[1])


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
            oldpoints = common.load_rider_points(rider_points_path=rider_points_path)

            spot_js_url = 'http://trackleaders.com/spot/{}/{}.js'.format(args.race, rider['url_fragment'])
            spot_js_response = common.retry(functools.partial(session.get, spot_js_url))
            spot_js_response.raise_for_status()
            newpoints = parse_points_from_spotjs_text(spot_js_response.text)

            points_set = set(itertools.chain(oldpoints, newpoints))
            points_sorted = [common.point_to_raw(point) for point in sorted(points_set)]
            if not points_sorted:
                logging.warning('No points for {name}.'.format(**rider))
            with common.DelayedKeyboardInterrupt():
                if not os.path.exists(rider_path):
                    os.mkdir(rider_path)
                with open(rider_points_path, 'w') as f:
                    json.dump(points_sorted, f, indent=2, sort_keys=True)

        except Exception:
            logging.exception('Error for {name}'.format(**rider))

