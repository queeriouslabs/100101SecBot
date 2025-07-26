#!/usr/bin/env python

import os
from distutils.core import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()


setup(name='Secbot',
      version='1.0',
      description="A security bot to guard your secret rebel hideout.",
      author="Matt Arcidy",
      author_email="matt@queeriouslabs.com",
      url="https://github.com/queeriouslabs/100101SecBot/",
      packages=['secbot']
      )
