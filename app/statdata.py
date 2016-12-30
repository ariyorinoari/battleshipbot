# -*- coding: utf-8 -*-
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
    redis.hset(userId,'imageUrl',image_url)

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
    return 'xxxxxxxx'

def setStat(userId,newStatus):
    pass

def isValidKey(userId):
    #redisにキーとして登録されているかチェック
    return True

def getEnemyName(myUserId):
    return 'teki'

def getKeyFromDisplayName(userName):
    return 'xxxxxxxxxx'

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
