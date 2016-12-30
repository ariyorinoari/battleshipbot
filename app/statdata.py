import redis

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
