#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import versioneer

long_description = """
This library provides a Python wrapper for the UNICORE REST API, making common tasks like file access, job submission and management, workflow submission and management more convenient, and integrating UNICORE features better with typical Python usage.

Visit https://github.com/HumanBrainProject/pyunicore for more information.
"""

python_requires = '>=3'

install_requires = [
    'PyJWT>=2.0',
    'requests>=2.5'
    'dataclasses>=0.8',
]

extras_require={
        'fuse'  : ['fusepy>=3.0.1'],
        'crypto': ['cryptography>=3.3.1'],
        'fs'    : ['fs>=2.4.0']
}

setup(
    name="pyunicore",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    packages=find_packages(),
    author="Bernd Schuller",
    author_email="b.schuller@fz-juelich.de",
    description="Python library for using the UNICORE REST API",
    long_description=long_description,
    python_requires=python_requires,
    install_requires=install_requires,
    extras_require = extras_require,
    entry_points = {
        'fs.opener': [
            'uftp = pyunicore.uftpfs:UFTPOpener',
        ]
    },
    license="License :: OSI Approved :: BSD",
    url='https://github.com/HumanBrainProject/pyunicore',
)
