# -*- coding: utf-8 -*-

import os

IMAGEMAP_ELEMENT_WIDTH = 260
IMAGEMAP_ELEMENT_HEIGHT = 197
BUTTON_ELEMENT_WIDTH = 520
BUTTON_ELEMENT_HEIGHT = 178
FIELD_IMAGE_FILENAME = 'map-{0}.png'
KQ_IMAGE_FILENAME = 'kq-{0}.png'
AM_IMAGE_FILENAME = 'am-{0}.png'
IMG_PATH = os.path.join(os.path.dirname(__file__), 'static', 'map')
TMP_ROOT_PATH = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
BG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'map', 'map-700.png')
#HEROKU_SERVER_URL = 'https://s-battleship.herokuapp.com/'
HEROKU_SERVER_URL = 'https://smbot161201.herokuapp.com/'
