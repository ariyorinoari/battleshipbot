# -*- coding:utf-8 -*-

from const import *
import errno
import os
from random import randint


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

entry = {
    '0':'+75+75',
    '1':'+335+75',
    '2':'+595+75',
    '3':'+855+75',
    '4':'+75+338',
    '5':'+335+338',
    '6':'+595+338',
    '7':'+855+338',
    '8':'+75+601',
    '9':'+335+601',
    '10':'+595+601',
    '11':'+855+601',
}

def generate_voting_result_image(data):
    number, path = _tmpdir()
    for i in range(0, 12):
        cmd = _generate_cmd(i, data, path)
        os.system(cmd)
    return number

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

