#!/usr/bin/env python

import setuptools

setuptools.setup(
    name='trackleaders_scraper',
    include_package_data=True,
    install_requires=[
        'requests',
        'beautifulsoup4',
    ],
    scripts=[
        'getriders',
    ]
)

