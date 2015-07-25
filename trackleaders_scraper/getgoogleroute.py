#!/usr/bin/env python

import os
import logging
import json

import requests

import trackleaders_scraper.common as common


def main():
    args = common.get_base_argparser().parse_args()
    common.configure_logging(args)

    race_path = common.get_race_path(args.race)

    with open(os.path.join(race_path, 'riders.json')) as f:
        riders = json.load(f)

    session = requests.Session()
    all_pairs = []

    for rider in riders:
        try:
            logging.info('Getting google routes for {name}'.format(**rider))
            rider_path = os.path.join(race_path, rider['url_fragment'])
            rider_points = common.load_rider_points(rider_path=rider_path)

            requests_waypoints = set()
            current_request_waypoints = None
            for point1, point2 in zip(rider_points[:-1], rider_points[1:]):
                dist = common.geodesic.Inverse(point1.lat, point1.lng, point2.lat, point2.lng)['s12']
                speed = dist / (point2.timestamp - point1.timestamp).total_seconds()  # UOM = m/s
                if speed > 1.388: # m/s = 5 km/h
                    if current_request_waypoints is None:
                        current_request_waypoints = [point1]
                    current_request_waypoints.append(point2)
                    if len(current_request_waypoints) == 10:
                        requests_waypoints.add(tuple(current_request_waypoints))
                        current_request_waypoints = None
                else:
                    if current_request_waypoints is not None:
                        # Treat the last point a the destination of a stop
                        requests_waypoints.add(tuple(current_request_waypoints))
                        current_request_waypoints = None

            # Don't add a unfull current_request_waypoints.

            google_routes_path =  os.path.join(rider_path, 'google_routes.json')
            if os.path.exists(google_routes_path):
                with open(google_routes_path) as f:
                    google_routes_raw = json.load(f)
            else:
                google_routes_raw = []
            
            google_routes = {tuple((common.raw_to_point(wp) for wp in route['waypoints'])): route['route']
                             for route in google_routes_raw}

            for request_waypoints in requests_waypoints - google_routes.keys():
                try:
                    params = {
                        'origin': '{lat},{lng}'.format(**vars(request_waypoints[0])),
                        'destination': '{lat},{lng}'.format(**vars(request_waypoints[-1])),
                        'waypoints': '|'.join(['via:{lat},{lng}'.format(**vars(wp)) for wp in request_waypoints[1:-1]]),
                        'sensor': 'false',
                        'avoid': 'highways',
                        'mode': 'bicycling',
                        'key': common.get_google_api_key(),
                    }
                    route_response = session.get('https://maps.googleapis.com/maps/api/directions/json', params=params).json()
                    if route_response['status'] == 'ZERO_RESULTS':
                        #  Try with driving directions
                        params['mode'] = 'driving'
                        route_response = session.get('https://maps.googleapis.com/maps/api/directions/json', params=params).json()
                    if route_response['status'] != 'OK':
                        logging.error('Error from google api: {} params: {}'.format(route_response['status'],params ))
                    else:
                        google_routes[request_waypoints] = route_response['routes'][0]
                except Exception:
                    logging.exception('Error for {name} getting route'.format(**rider))

            for request_waypoints in google_routes.keys() - requests_waypoints:
                del google_routes[request_waypoints]

            google_routes_sorted = sorted(google_routes.items(), key=lambda route: route[0][0].timestamp)
            google_routes_raw = [{'waypoints': [common.point_to_raw(wp) for wp in waypoints], 'route': route}
                                 for waypoints, route in google_routes_sorted]
            with common.DelayedKeyboardInterrupt():
                if not os.path.exists(rider_path):
                    os.mkdir(rider_path)
                with open(google_routes_path, 'w') as f:
                    json.dump(google_routes_raw, f, indent=2, sort_keys=True)

        except Exception:
            logging.exception('Error for {name}'.format(**rider))

    print(len(all_pairs))
