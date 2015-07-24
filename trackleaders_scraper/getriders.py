#!/usr/bin/env python
from urllib.parse import urlparse, parse_qs
import json
import os
import logging
import re

import bs4

import trackleaders_scraper.common as common


def parse_riders_from_race_page(race_page_text):
    race_page = bs4.BeautifulSoup(race_page_text, "html.parser")
    rider_links = (
        race_page
        .find(string=re.compile('All Riders.*'))
        .find_parent('h3')
        .next_sibling
        .find_all('a', title="Click for individual history")
    )
    return [
        {
            'url_fragment': parse_qs(urlparse(rider_link['href']).query)['name'][0],
            'name': rider_link.string,
        }
        for rider_link in rider_links
    ]


def main():
    args = common.get_base_argparser().parse_args()
    common.configure_logging(args)

    logging.info('Getting Riders')

    session = common.get_trackleaders_session()

    race_page_response = session.get('http://trackleaders.com/{}f.php'.format(args.race))
    race_page_response.raise_for_status()
    riders = parse_riders_from_race_page(race_page_response.text)

    race_path = common.get_race_path(args.race)
    if not os.path.exists(race_path):
        os.mkdir(race_path)

    with open(common.get_riders_path(race_path), 'w') as f:
        json.dump(riders, f, indent=2, sort_keys=True)
