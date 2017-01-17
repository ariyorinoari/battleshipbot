# -*- coding:utf-8 -*-

import errno
import os
from random import randint

from const import *
from statdata import *

def make_static_dir(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def getSourceId(source):
    sourceType = source.type
    if sourceType == 'user':
        return source.user_id
    elif sourceType == 'group':
        return source.group_id
    elif sourceType == 'room':
        return source.room_id
    else:
        raise NotFoundSourceError()

class NotFoundSourceError(Exception):
    pass

#173,130
entry = {
    '1':'+7+7',
    '2':'+180+7',
    '3':'+353+7',
    '4':'+526+7',
    '5':'+7+137',
    '6':'+180+137',
    '7':'+353+137',
    '8':'+526+137',
    '9':'+7+267',
    '10':'+180+267',
    '11':'+353+267',
    '12':'+526+267',
    '13':'+7+397',
    '14':'+180+397',
    '15':'+353+397',
    '16':'+526+397',
}

def generate_map_image(king_position,queen_position):
    number, path = _tmpdir()

    if king_position != '-':
        cmd = _composite_king_cmd(king_position, BG_FILE_PATH, os.path.join(path, 'temp.png'))
        os.system(cmd)
    if queen_position != '-':
        cmd = _composite_queen_cmd(queen_position, os.path.join(path, 'temp.png'), os.path.join(path, 'map.png'))
        os.system(cmd)

    for size in [240, 300, 460, 700, 1040]:
        resize_cmd = _resize_cmd(path, size)
        os.system(resize_cmd)
    return number

def _resize_cmd(path, size):
    before = path + '/map.png'
    after = path + '/map-' + str(size) + '.png'
    cmd = []
    cmd.append('convert -resize')
    cmd.append(str(size) + 'x')
    cmd.append(before)
    cmd.append('-quality 00')
    cmd.append(after)
    return ' '.join(cmd)

def _composite_king_cmd(position, bg_file, out_file):

    cmd = []
    cmd.append('composite -gravity northwest -geometry')
    cmd.append(entry[str(position)])
    cmd.append('-compose over')
    cmd.append(os.path.join(IMG_PATH, 'king.png'))
    cmd.append(bg_file)
    cmd.append(out_file)
    return ' '.join(cmd)

def _composite_queen_cmd(position,bg_file, out_file):

    cmd = []
    cmd.append('composite -gravity northwest -geometry')
    cmd.append(entry[str(position)])
    cmd.append('-compose over')
    cmd.append(os.path.join(IMG_PATH, 'queen.png'))
    cmd.append(bg_file)
    cmd.append(out_file)
    return ' '.join(cmd)

def _generate_cmd(position, data, tmp):
    if position is 0:
        bg_file = BG_FILE_PATH
        out_file = os.path.join(tmp, 'result_0.png')
    else:
        bg_file = os.path.join(tmp, 'result_' + str(position-1) + '.png')
        out_file = os.path.join(tmp, 'result_' + str(position) + '.png')
    value = data[str(position)] if data.has_key(str(position)) else str(0)
    cmd = []
    cmd.append('composite -gravity northwest -geometry')
    cmd.append(entry[str(position)])
    cmd.append('-compose over')
    cmd.append(os.path.join(IMG_PATH, 'vote_' + value + '.png'))
    cmd.append(bg_file)
    cmd.append(os.path.join(tmp, out_file))
    return ' '.join(cmd)

def _tmpdir():
    number = str(randint(1000, 9999))
    path = os.path.join(TMP_ROOT_PATH, number)
    make_static_dir(path)
    return (number, path)
