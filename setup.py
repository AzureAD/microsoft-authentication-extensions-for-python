#!/usr/bin/env python

from setuptools import setup, find_packages
import re, io

__version__ = re.search(
    r'__version__\s*=\s*[rRfFuU]{0,2}[\'"]([^\'"]*)[\'"]',
    io.open('msal_extensions/__init__.py', encoding='utf_8_sig').read()
    ).group(1)

long_description = open('README.md').read()

setup(
    name='msal-extensions',
    version=__version__,
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_data={'': ['LICENSE']},
    python_requires=">=3.7",
    install_requires=[
        'msal>=1.27,<1.29',  # MSAL Python 1.29+ may not have TokenCache._find()
        'portalocker<3,>=1.4',

        ## We choose to NOT define a hard dependency on this.
        # "pygobject>=3,<4;platform_system=='Linux'",
    ],
    tests_require=['pytest'],
)
