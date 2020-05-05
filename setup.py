#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import versioneer

long_description = open("README.md").read()

setup(
    name="pyunicore",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    packages=find_packages(),
    author="Bernd Schuller",
    author_email="b.schuller@fz-juelich.de",
    description="Python helper functions for using the UNICORE REST API",
    long_description=long_description,
    license="License :: OSI Approved :: BSD",
    url='http://www.humanbrainproject.eu',
)
