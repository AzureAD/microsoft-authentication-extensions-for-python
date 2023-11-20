#!/usr/bin/env python

from setuptools import setup, find_packages
import re, io

__version__ = re.search(
    r'__version__\s*=\s*[rRfFuU]{0,2}[\'"]([^\'"]*)[\'"]',
    io.open('msal_extensions/__init__.py', encoding='utf_8_sig').read()
    ).group(1)

try:
    long_description = open('README.md').read()
except OSError:
    long_description = "README.md is not accessible on TRAVIS CI's Python 3.5"

setup(
    name='msal-extensions',
    version=__version__,
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_data={'': ['LICENSE']},
    python_requires=">=3.7",
    install_requires=[
        'msal>=0.4.1,<2.0.0',

        "portalocker<3,>=1.0;platform_system!='Windows'",
        "portalocker<3,>=1.6;platform_system=='Windows'",

        ## We choose to NOT define a hard dependency on this.
        # "pygobject>=3,<4;platform_system=='Linux'",

        # Packaging package uses YY.N versioning so we have no upperbound to pin.
        # Neither do we need lowerbound because its `Version` API existed since its first release
        # https://github.com/pypa/packaging/blame/14.0/packaging/version.py
        'packaging',
    ],
    tests_require=['pytest'],
)
