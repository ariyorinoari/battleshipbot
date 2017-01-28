# -*- coding: utf-8 -*-
from flask import Flask, request, abort, send_from_directory, url_for
import redis
from random import randint,sample

app = Flask(__name__)
app.config.from_object('config')
redis = redis.from_url(app.config['REDIS_URL'])

def generateGameKey():
    new_game_key = redis.incrby('maxGameKey',randint(3,7))
    return str(new_game_key)

def memberIdAdd(userId):
    if redis.sismember('memberKeyList',userId) == 0:
        redis.sadd('memberKeyList',userId)
        game_key = generateGameKey()
        redis.hset('gameKeyList',game_key,userId)
    else:
        game_key = getGameKey(userId)
    return game_key

def memberIdRemove(userId,game_key):
    if redis.sismember('memberKeyList',userId) == 1:
        redis.srem('memberKeyList',userId)
        redis.hdel('gameKeyList',game_key)

def getGameKey(userId):
    return redis.hget(userId,'gameKey')

def createHashData(userId,display_name,game_key):
    if isinstance(display_name,str):
        display_name = display_name.decode('utf-8')
    redis.hset(userId,'displayName',display_name)
    redis.hset(userId,'gameKey',game_key)
    redis.hset(userId,'status','normal')

    redis.hset(userId,'enemyId','-')
    redis.hset(userId,'buttonStatus','-')
    redis.hset(userId,'KingOrderStatus','notyet')
    redis.hset(userId,'QueenOrderStatus','notyet')
    redis.hset(userId,'KingHP',2)
    redis.hset(userId,'QueenHP',1)
    redis.hset(userId,'KingPosition','-')
    redis.hset(userId,'QueenPosition','-')

def updateDisplayName(sourceId,display_name):
    if isinstance(display_name,str):
        display_name = display_name.decode('utf-8')
    redis.hset(sourceId,'displayName',display_name)

def clearHashData(userId):
    redis.hset(userId,'status','normal')
    redis.hset(userId,'enemyId','-')
    redis.hset(userId,'buttonStatus','-')
    redis.hset(userId,'KingOrderStatus','notyet')
    redis.hset(userId,'QueenOrderStatus','notyet')
    redis.hset(userId,'KingHP',2)
    redis.hset(userId,'QueenHP',1)
    redis.hset(userId,'KingPosition','-')
    redis.hset(userId,'QueenPosition','-')

def createComData(userId):
    redis.hset('com_'+userId,'KingOrderStatus','notyet')
    redis.hset('com_'+userId,'QueenOrderStatus','notyet')
    redis.hset('com_'+userId,'KingHP',2)
    redis.hset('com_'+userId,'QueenHP',1)
    pos_list = sample(range(16),2)
    redis.hset('com_'+userId,'KingPosition',str(pos_list[0]+1))
    redis.hset('com_'+userId,'QueenPosition',str(pos_list[1]+1))

def removeHashData(userId):
    redis.delete(userId)

def addRecordData(userId,enemyId,enemy_key,enemy_name):
    if isinstance(enemy_name,str):
        enemy_name = enemy_name.decode('utf-8')
    redis.hset(u'rec_'+userId,enemyId,enemy_name+' / '+enemy_key)

def getRecordData(userId):
    return redis.hgetall('rec_'+userId)

def getEnemyId(userId):
    return redis.hget(userId,'enemyId')

def setEnemy(userId,enemyId):
    redis.hset(userId,'enemyId',enemyId)

def getStat(userId):
    return redis.hget(userId,'status')

def setStat(userId,newStatus):
    redis.hset(userId,'status',newStatus)

def getButtonStat(userId):
    return redis.hget(userId,'buttonStatus')

def setButtonStat(userId,newStatus):
    redis.hset(userId,'buttonStatus',newStatus)


def isValidKey(game_key):
    #redisにキーとして登録されているかチェック
    if redis.hget('gameKeyList',game_key) is None:
        return False
    else:
        return True

def getSourceIdfromGK(game_key):
        return redis.hget('gameKeyList',game_key)

def getEnemyName(myUserId):
    enemyId = redis.hget(myUserId,'enemyId')
    return redis.hget(enemyId,'displayName')

def getDisplayName(myUserId):
    return redis.hget(myUserId,'displayName')

def getKingPosition(userId):
    return redis.hget(userId,'KingPosition')

def _setPosition(userId,posName,current_position,positionNum):
    position = int(positionNum)
    if position < 1 or position > 16:
        return False
    if current_position == '-':
        if isVacant(userId,positionNum):
            redis.hset(userId,posName,positionNum)
            return True
        else:
            return False
    else:
        if isAvailablePosition(current_position,positionNum) and isVacant(userId,positionNum):
            redis.hset(userId,posName,positionNum)
            return True
        else:
            return False

def setKingPosition(userId,positionNum):
    return _setPosition(userId,'KingPosition',
        redis.hget(userId,'KingPosition'),positionNum)

def setQueenPosition(userId,positionNum):
    return _setPosition(userId,'QueenPosition',
        redis.hget(userId,'QueenPosition'),positionNum)

def getQueenPosition(userId):
    return redis.hget(userId,'QueenPosition')


def setAttackPosition(userId,fromPosition,toPosition):
    if isPositionAround(fromPosition,toPosition) == True:
        return isVacant(userId,toPosition)
    else:
        return False

def isKingDying(userId):
    if redis.hget(userId,'KingHP') == '1':
        return True
    else:
        return False

def getAttackImpact(attackedId,position):

    return_msg = u''

    if getKingPosition(attackedId) != '-':
        if position == getKingPosition(attackedId):
            return_msg += u'Kingに命中しました！'
            if int(redis.hincrby(attackedId,'KingHP',-1)) == 0:
                return_msg += u'Kingが行動不能になりました\uD83D\uDE32'
                setKingOrderStatus(attackedId,'killed')
                redis.hset(attackedId,'KingPosition','-')
        elif isPositionAround(position,getKingPosition(attackedId)) == True:
            return_msg += u'Kingにかすりました。'

    if getQueenPosition(attackedId) != '-':
        if position == getQueenPosition(attackedId):
            return_msg += u'Queenに命中しました！'
            if int(redis.hincrby(attackedId,'QueenHP',-1)) == 0:
                return_msg += u'Queenが行動不能になりました\uD83D\uDE32'
                setQueenOrderStatus(attackedId,'killed')
                redis.hset(attackedId,'QueenPosition','-')
        elif isPositionAround(position,getQueenPosition(attackedId)) == True:
            return_msg += u'Queenにかすりました。'

    return return_msg


def isPositionAround(src_pos,dst_pos):
    from_int = int(src_pos)
    to_int = int(dst_pos)

    if from_int ==  1:
        if to_int == 2 or to_int == 5 or to_int == 6:
            return True
        else:
            return False
    elif from_int == 2 or from_int == 3:
        if to_int == from_int - 1 or to_int == from_int + 1:
            return True
        elif to_int == from_int + 3 or to_int == from_int + 4 or to_int == from_int +5:
            return True
        else:
            return False
    elif from_int == 4:
        if to_int == 3 or to_int == 7 or to_int == 8:
            return True
        else:
            return False
    elif from_int == 5 or from_int == 9:
        if to_int == from_int - 4 or to_int == from_int -3:
            return True
        elif to_int == from_int +1:
            return True
        elif to_int == from_int +4 or to_int == from_int +5:
            return True
        else:
            return False
    elif from_int == 6 or from_int == 7 or from_int == 10 or from_int == 11:
        if to_int == from_int -5 or to_int == from_int -4 or to_int == from_int -3:
            return True
        elif to_int == from_int -1 or to_int == from_int + 1:
            return True
        elif to_int == from_int + 3 or to_int == from_int +4 or to_int == from_int +5:
            return True
        else:
            return False
    elif from_int == 8 or from_int == 12:
        if to_int == from_int - 5 or to_int == from_int -4:
            return True
        elif to_int == from_int -1:
            return True
        elif to_int == from_int +3 or to_int == from_int +4:
            return True
        else:
            return False
    elif from_int ==  13:
        if to_int == 9 or to_int == 10 or to_int == 14:
            return True
        else:
            return False
    elif from_int == 14 or from_int == 15:
        if to_int == from_int - 5 or to_int == from_int -4 or to_int == from_int -3:
            return True
        elif to_int == from_int -1 or to_int == from_int +1:
            return True
        else:
            return False
    elif from_int ==  16:
        if to_int == 11 or to_int == 12 or to_int == 15:
            return True
        else:
            return False

def getKingOrderStatus(userId):
    return redis.hget(userId,'KingOrderStatus')

def setKingOrderStatus(userId,status):
    redis.hset(userId,'KingOrderStatus',status)

def getQueenOrderStatus(userId):
    return redis.hget(userId,'QueenOrderStatus')

def setQueenOrderStatus(userId,status):
    redis.hset(userId,'QueenOrderStatus',status)

def getDistance(before,after,isStealth):
    before_int = int(before)
    after_int = int(after)
    if before_int > after_int:
        if before_int % 4 == after_int % 4:
            if isStealth:
                return_msg = '上方向に移動しました'
            else:
                move_dist = before_int/4 - after_int/4
                return_msg = '上方向に'+str(move_dist)+'歩 移動しました'
        else:
            if isStealth:
                return_msg = '左方向に移動しました'
            else:
                move_dist = before_int - after_int
                return_msg = '左方向に'+str(move_dist)+'歩 移動しました'
    else:
        if before_int % 4 == after_int % 4:
            if isStealth:
                return_msg = '下方向に移動しました'
            else:
                move_dist = after_int/4 - before_int/4
                return_msg = '下方向に'+str(move_dist)+'歩 移動しました'
        else:
            if isStealth:
                return_msg = '右方向に移動しました'
            else:
                move_dist = after_int - before_int
                return_msg = '右方向に'+str(move_dist)+'歩 移動しました'
    return return_msg

def isAvailablePosition(current,future):
#飛車（縦横方向移動のみ）の動きになっているかチェック
    if current == future:
        return False

    current_int = int(current)
    future_int = int(future)
    if future_int > 16 or future_int < 1:
        return False

    if current == '1' or current == '5' or current == '9' or current == '13':
        if (future_int > current_int and future_int < current_int + 4) or \
            future_int % 4 == 1 :
            return True
        else:
            return False
    elif current == '2' or current == '6' or current == '10' or current == '14':
        if (future_int > current_int -2 and future_int < current_int + 3) or \
            future_int % 4 == 2 :
            return True
        else:
            return False
    elif current == '3' or current == '7' or current == '11' or current == '15':
        if (future_int > current_int -3 and future_int < current_int + 2) or \
            future_int % 4 == 3 :
            return True
        else:
            return False
    elif current == '4' or current == '8' or current == '12' or current == '16':
        if (future_int > current_int -4 and future_int < current_int) or \
            future_int % 4 == 0 :
            return True
        else:
            return False

def isVacant(userId,future):
    if redis.hget(userId,'KingPosition') != future and \
        redis.hget(userId,'QueenPosition') != future:
        return True
    else:
        return False

def addNotHereList(sourceId,position):
    if redis.sismember('com_'+sourceId+'_posrec',position) == 0:
        redis.sadd('com_'+sourceId+'_posrec',position)

def clearNotHereList(sourceId):
    redis.delete('com_'+sourceId+'_posrec')

def notInClearedList(sourceId,position):
    if redis.sismember('com_'+sourceId+'_posrec',position) == 1:
        return False
    else:
        return True
