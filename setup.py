#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

long_description = open("README.md").read()

setup(
    name="pyunicore",
    version='0.1.0',
    packages=find_packages(),
    author="Bernd Schuller",
    author_email="b.schuller@fz-juelich.de",
    description="Python helper functions for using the UNICORE REST API",
    long_description=long_description,
    license="License :: OSI Approved :: BSD",
    url='http://www.humanbrainproject.eu',
)
