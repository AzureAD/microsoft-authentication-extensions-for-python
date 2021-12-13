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
    install_requires=[
        'msal>=0.4.1,<2.0.0',

        # In order to implement these requirements:
        #       Lowerbound = (1.6 if playform_system == 'Windows' else 1.0)
        #       Upperbound < (3 if python_version >= '3.5' else 2)
        # The following 4 lines use the `and` syntax defined here:
        #       https://www.python.org/dev/peps/pep-0508/#grammar
        "portalocker<3,>=1.0;python_version>='3.5' and platform_system!='Windows'",
        "portalocker<2,>=1.0;python_version=='2.7' and platform_system!='Windows'",
        "portalocker<3,>=1.6;python_version>='3.5' and platform_system=='Windows'",
        "portalocker<2,>=1.6;python_version=='2.7' and platform_system=='Windows'",

        "pathlib2;python_version<'3.0'",
        ## We choose to NOT define a hard dependency on this.
        # "pygobject>=3,<4;platform_system=='Linux'",
    ],
    tests_require=['pytest'],
)
