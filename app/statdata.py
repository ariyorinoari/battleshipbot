# -*- coding: utf-8 -*-
from flask import Flask, request, abort, send_from_directory, url_for
import redis

app = Flask(__name__)
app.config.from_object('config')
redis = redis.from_url(app.config['REDIS_URL'])

def memberIdAdd(userId):
    if redis.sismember('memberKeyList',userId) == 0:
        redis.sadd('memberKeyList',userId)

def memberIdRemove(userId):
    if redis.sismember('memberKeyList',userId) == 1:
        redis.srem('memberKeyList',userId)

def createHashData(userId,display_name,image_url):
    if isinstance(display_name,str):
        display_name = display_name.decode('utf-8')
    redis.hset(userId,'displayName',display_name)
#    redis.hset(userId,'imageUrl',image_url)
    redis.hset(userId,'status','normal')

    redis.hset(userId,'enemyId','-')
    redis.hset(userId,'KingOrderStatus','notyet')
    redis.hset(userId,'QueenOrderStatus','notyet')
    redis.hset(userId,'KingHP',2)
    redis.hset(userId,'QueenHP',1)
    redis.hset(userId,'KingPosition','-')
    redis.hset(userId,'QueenPosition','-')

def clearHashData(userId):
    redis.hset(userId,'status','normal')
    redis.hset(userId,'enemyId','-')
    redis.hset(userId,'KingOrderStatus','notyet')
    redis.hset(userId,'QueenOrderStatus','notyet')
    redis.hset(userId,'KingHP',2)
    redis.hset(userId,'QueenHP',1)
    redis.hset(userId,'KingPosition','-')
    redis.hset(userId,'QueenPosition','-')

def removeHashData(userId):
    redis.delete(userId)

def getEnemyId(userId):
    return redis.hget(userId,'enemyId')

def setEnemy(userId,enemyId):
    redis.hset(userId,'enemyId',enemyId)

def getStat(userId):
    return redis.hget(userId,'status')

def setStat(userId,newStatus):
    redis.hset(userId,'status',newStatus)

def isValidKey(userId):
    #redisにキーとして登録されているかチェック
    if redis.sismember('memberKeyList',userId) == 0:
        return False
    else:
        return True

def getEnemyName(myUserId):
    enemyId = redis.hget(myUserId,'enemyId')
    return redis.hget(enemyId,'displayName')

def getDisplayName(myUserId):
    return redis.hget(myUserId,'displayName')

def getKingPosition(userId):
    return redis.hget(userId,'KingPosition')

def setKingPosition(userId,positionNum):
    position = int(positionNum)
    if position < 1 or position > 16:
        return False

    current_position = redis.hget(userId,'KingPosition')
    if current_position == '-':
        if isVacant(userId,positionNum):
            redis.hset(userId,'KingPosition',positionNum)
            return True
        else:
            return False
    else:
        if isAvailablePosition(current_position,positionNum) and isVacant(userId,positionNum):
            redis.hset(userId,'KingPosition',positionNum)
            return True
        else:
            return False

def getQueenPosition(userId):
    return redis.hget(userId,'QueenPosition')

def setQueenPosition(userId,positionNum):
    position = int(positionNum)
    if position < 1 or position > 16:
        return False

    current_position = redis.hget(userId,'QueenPosition')
    if current_position == '-':
        if isVacant(userId,positionNum):
            redis.hset(userId,'QueenPosition',positionNum)
            return True
        else:
            return False
    else:
        if isAvailablePosition(current_position,positionNum) and isVacant(userId,positionNum):
            redis.hset(userId,'QueenPosition',positionNum)
            return True
        else:
            return False

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
