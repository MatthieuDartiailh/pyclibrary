#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

import os.path

version_py = os.path.join(os.path.dirname(__file__), 'pyclibrary',
                          'version.py')
with open(version_py, 'r') as f:
    d = dict()
    exec(f.read(), d)
    version = d['__version__']

setup(
    name = 'pyclibrary',
    description = 'C binding automation',
    version = version,
    long_description = '''PyCLibrary includes 1) a pure-python C parser and
2) an automation library that uses C header file definitions to simplify the
use of c bindings. The C parser currently processes all macros, typedefs,
structs, unions, enums, function prototypes, and global variable declarations,
and can evaluate typedefs down to their fundamental C types +
pointers/arrays/function signatures. Pyclibrary can automatically build c
structs/unions and perform type conversions when calling functions via
cdll/windll.''',
    author = 'PyCLibrary Developers',
    author_email = 'm.dartiailh@gmail.com',
    url = 'http://github.com/MatthieuDartiailh/pyclibrary',
    download_url = 'http://github.com/MatthieuDartiailh/pyclibrary/tarball/master',
    keywords = 'C binding automation',
    license = 'MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3'
        ],
    zip_safe = False,
    packages = ['pyclibrary', 'pyclibrary.backends', 'pyclibrary.thirdparty'],
	package_data = {'pyclibrary': ['headers/*']},
    requires = ['future'],
    install_requires = ['future'],
)

