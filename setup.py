#!/usr/bin/env python

from setuptools import setup, find_packages

__version__ = "0.0.1"

setup(
    name='msal-extensions',
    version=__version__,
    packages=find_packages(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
    ],
    extra_require={
        'dev': [
            'pytest',
        ]
    }

)
