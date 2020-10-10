#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2018 Stephen Wasilewski
# =======================================================================
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# =======================================================================
"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['click', 'sphinx-click', 'future', 'configparser', 'docutils',
                'sphinx']

setup_requirements = ['pytest-runner']

test_requirements = ['pytest', ]

packages = ['clasp']

data_files = []

package_data = {}

console_scripts = []

setup(
    author="Stephen Wasilewski",
    author_email='stephanwaz@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="clasp is  tools for command line and subprocess script development",
    entry_points={"console_scripts": ['clasp_template=clasp.templates:main']},
    python_requires=">=3.6",
    install_requires=requirements,
    license="Mozilla Public License 2.0 (MPL 2.0)",
    long_description=readme,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='clasp',
    name='clasp',
    packages=find_packages(include=packages),
    data_files=data_files,
    package_data=package_data,
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://bitbucket.org/stephenwasilewski/clasp',
    project_urls= {'documentation': 'https://clasp.readthedocs.io/'},
    version='1.1.2',
    zip_safe=True,
)
