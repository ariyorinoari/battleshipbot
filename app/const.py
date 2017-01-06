# -*- coding: utf-8 -*-

import os

POKER_MUTEX_TIMEOUT = 20
POKER_MUTEX_KEY_PREFIX = 'MUTEX_POCKER_'
POKER_IMAGEMAP_ELEMENT_WIDTH = 260
POKER_IMAGEMAP_ELEMENT_HEIGHT = 197
VOTE_MUTEX_TIMEOUT = 10
VOTE_MUTEX_KEY_PREFIX = 'MUTEX_VOTE_'
POKER_IMAGE_FILENAME = 'map-{0}.png'
IMG_PATH = os.path.join(os.path.dirname(__file__), 'static', 'map')
TMP_ROOT_PATH = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
BG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'map', 'map-700.png')
MESSAGE_END_POKER = '#{0}のポーカーは終了してまーす'
MESSAGE_INVALID_VOTE = '#{0}のポーカーはないですよ。手入力した？'
HEROKU_SERVER_URL = 'https://s-battleship.herokuapp.com/'
