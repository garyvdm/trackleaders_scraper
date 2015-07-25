#!/usr/bin/env python

import setuptools

setuptools.setup(
    name='trackleaders_scraper',
    include_package_data=True,
    packages=['trackleaders_scraper'],
    install_requires=[
        'requests',
        'beautifulsoup4',
        'slimit',  # for parsing js to an ast.
        'python-dateutil',
        'pytz',
        'aniso8601',
        'geographiclib',
    ],
    entry_points={
        'console_scripts': [
            'getriders = trackleaders_scraper.getriders:main',
            'getpoints = trackleaders_scraper.getpoints:main',
            'getgoogleroutes = trackleaders_scraper.getgoogleroute:main',
        ],
    }
)

