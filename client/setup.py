#!/bin/env python

import os
from setuptools import setup


package_name = 'conduit-client'
version = '0.1'
readme = os.path.join(os.path.dirname(__file__), 'README.rst')
with open(readme) as readme_file:
    long_description = readme_file.read()


setup(
    name = package_name,
    version = version,
    install_requires=['paramiko', 'python-ddns'],
    description = "Client for homeland social's coduit.",
    long_description = long_description,
    author = 'Ben Timby',
    author_email = 'btimby@gmail.com',
    maintainer = 'Ben Timby',
    maintainer_email = 'btimby@gmail.com',
    url = 'http://github.com/shanty-social/conduit/',
    license = 'MIT',
    packages = ['conduit_client'],
    classifiers = (
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
