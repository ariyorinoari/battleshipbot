# -*- coding: utf-8 -*-

import logging
import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))

# get channel_secret and channel_access_token from your environment variable
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', None)
if CHANNEL_SECRET is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)

CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if CHANNEL_ACCESS_TOKEN is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

REDIS_URL = os.getenv('REDIS_URL', None)
if REDIS_URL is None:
    print('Specify REDIS_URL as environment variable.')
    sys.exit(1)

LOG_LEVEL = logging.INFO
