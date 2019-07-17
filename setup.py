#!/usr/bin/env python

from setuptools import setup, find_packages
import re, io

__version__ = re.search(
    r'__version__\s*=\s*[rRfFuU]{0,2}[\'"]([^\'"]*)[\'"]',
    io.open('msal_extensions/__init__.py', encoding='utf_8_sig').read()
    ).group(1)

setup(
    name='msal-extensions',
    version=__version__,
    packages=find_packages(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
    ],
    install_requires=[
        'msal>=0.4.1,<0.6.0',
        'portalocker~=1.0',
    ],
    tests_require=['pytest'],
)
