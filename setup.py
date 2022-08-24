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
    'PyJWT>=1.7',
    'requests>=2.5'
]

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
    license="License :: OSI Approved :: BSD",
    url='https://github.com/HumanBrainProject/pyunicore',
)
