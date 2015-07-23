#!/usr/bin/env python

import setuptools

setuptools.setup(
    name='trackleaders_scraper',
    include_package_data=True,
    install_requires=[
        'requests',
        'beautifulsoup4',
        'slimit',  # for parsing js to an ast.
        'python-dateutil',
        'pytz',
        'aniso8601',
    ],
    scripts=[
        'getriders',
        'getpoints',
    ]
)

