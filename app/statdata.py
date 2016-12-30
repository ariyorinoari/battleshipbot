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

def memberNameAdd(display_name,userId):
    if redis.hexists('memberNameList',display_name) == 0:
        redis.hset('memberNameList',display_name,userId)
    else:
        #別ユーザーでdisplay_name の重複があり得る。重複時の対応について検討が必要
        pass

def memberNameRemove(display_name,userId):
    #別ユーザーでdisplay_name の重複があり得る。重複時の対応について検討が必要
    redis.hdel('memberNameList',display_name)

def createHashData(userId,display_name,image_url):
    redis.hset(userId,'displayName',display_name)
#    redis.hset(userId,'imageUrl',image_url)
    redis.hset(userId,'imageUrl','https://i0.wp.com/dashboard.heroku.com/images/static/ninja-avatar-48x48.png?ssl=1')
    redis.hset(userId,'status','normal')

    redis.hset(userId,'enemyId','-')
    redis.hset(userId,'KingOrderStatus','notyet')
    redis.hset(userId,'QueenOrderstatus','notyet')

def removeHashData(userId):
    redis.delete(userId)

def getEnemyId(userId):
    return 'xxxxxxxxxx'

def setEnemy(userId,enemyId):
    pass

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

def getKeyFromDisplayName(userName):
    return redis.hget('memberNameList',userName)

def getImage(userId):
    return redis.hget(userId,'imageUrl')

def setPreviousStat(userId,currentStat):
    pass

def getPreviousStat(userId):
    return 'battle_init'

def getKingPosition(userId):
    return '1'

def setKingPosition(userId,positionNum):
    return True

def getQueenPosition(userId):
    return '2'

def setQueenPosition(userId,positionNum):
    return True

def getKingOrderStatus(userId):
    return redis.hget(userId,'kingOrderStatus')

def getQueenOrderStatus(userId):
    return redis.hget(userId,'QueenOrderStatus')
