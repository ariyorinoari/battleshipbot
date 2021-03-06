#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import re

from flask import Flask, request, abort, send_from_directory, url_for

from linebot import (
    LineBotApi, WebhookHandler,
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    StickerMessage, StickerSendMessage,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, URITemplateAction, PostbackTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    UnfollowEvent, FollowEvent,ImageSendMessage,
    ImagemapSendMessage, MessageImagemapAction, BaseSize, ImagemapArea
)

app = Flask(__name__)
app.config.from_object('config')
line_bot_api = LineBotApi(app.config['CHANNEL_ACCESS_TOKEN'])


from random import randint,sample
from const import *
from utility import *
from statdata import *
import app as mainapp

def isComInitComplete(sourceId,reply_token,text):
    num_matcher = re.match(r'^[0-9]{1,}$',text)
    if num_matcher is None:
        line_bot_api.reply_message(
            reply_token,
            TextMessage(text='うまく認識できませんでした\uD83D\uDE22\n マップ上の1から16の数字をタップして、再度位置を入力してください'))
    else:
        if getKingPosition(sourceId) == '-':
            if setKingPosition(sourceId,num_matcher.group(0)) == False:
                line_bot_api.reply_message(
                    reply_token,
                    TextMessage(text='うまく認識できませんでした\uD83D\uDE22\n マップ上の1から16の数字でKingの位置を入力してください'))
                return 'err'
            else:
                return 'halfway'
        else:
            if setQueenPosition(sourceId,num_matcher.group(0)) == False:
                line_bot_api.reply_message(
                    reply_token,
                    TextMessage(text='うまく認識できませんでした\uD83D\uDE22\n マップ上の1から16の数字でQueenの位置を入力してください。Kingと同じ場所はダメですよ。'))
                return 'err'
            else:
                return 'complete'

def comBattleUserInput(sourceId,reply_token,text):
    matcher = re.match(r'(.*?)__(.*)', text)
    if matcher is not None and matcher.group(1) == 'KING':
        if getKingOrderStatus(sourceId) == 'ordered':
            line_bot_api.reply_message(reply_token, TextMessage(text='\uD83D\uDE22Kingはすでに行動済です'))
        elif getKingOrderStatus(sourceId) == 'killed':
            line_bot_api.reply_message(reply_token, TextMessage(text='Kingは行動不能です\uD83D\uDE22'))
        else:
            if matcher.group(2) == 'MOVE':
                line_bot_api.reply_message(
                    reply_token, TextMessage(text='Kingの移動先は\u2754'))
                setKingOrderStatus(sourceId,'move_position_wait')
                if getQueenOrderStatus(sourceId) == 'move_position_wait' or getQueenOrderStatus(sourceId) == 'attack_position_wait':
                    setQueenOrderStatus(sourceId,'notyet')
            elif matcher.group(2) == 'ATTACK':
                line_bot_api.reply_message(
                    reply_token, TextMessage(text='Kingの攻撃先は\u2754'))
                setKingOrderStatus(sourceId,'attack_position_wait')
                if getQueenOrderStatus(sourceId) == 'move_position_wait' or getQueenOrderStatus(sourceId) == 'attack_position_wait':
                    setQueenOrderStatus(sourceId,'notyet')

    elif matcher is not None and matcher.group(1) == 'QUEEN':
        if getQueenOrderStatus(sourceId) == 'ordered':
            line_bot_api.reply_message(
                reply_token, TextMessage(text='\uD83D\uDE22Queenはすでに行動済です'))
        elif getQueenOrderStatus(sourceId) == 'killed':
            line_bot_api.reply_message(reply_token,TextMessage(text='Queenは行動不能です\uD83D\uDE22'))
        else:
            if matcher.group(2) == 'MOVE':
                line_bot_api.reply_message(
                    reply_token, TextMessage(text='Queenの移動先は\u2754'))
                setQueenOrderStatus(sourceId,'move_position_wait')
                if getKingOrderStatus(sourceId) == 'move_position_wait' or getKingOrderStatus(sourceId) == 'attack_position_wait':
                    setKingOrderStatus(sourceId,'notyet')
            elif matcher.group(2) == 'ATTACK':
                line_bot_api.reply_message(
                    reply_token, TextMessage(text='Queenの攻撃先は\u2754'))
                setQueenOrderStatus(sourceId,'attack_position_wait')
                if getKingOrderStatus(sourceId) == 'move_position_wait' or getKingOrderStatus(sourceId) == 'attack_position_wait':
                    setKingOrderStatus(sourceId,'notyet')
    else:
        num_matcher = re.match(r'^[0-9]{1,}$',text)
        if text == 'KING':
            if getKingOrderStatus(sourceId) == 'killed':
                line_bot_api.push_message(
                    sourceId,TextSendMessage(text='Kingは行動不能です\uD83D\uDE22'))
            elif getKingOrderStatus(sourceId) == 'ordered':
                line_bot_api.push_message(
                    sourceId,TextSendMessage(text='Kingは行動済です\uD83D\uDE22'))
            else:
                setButtonStat(sourceId,'king_wait_action')
                mainapp.generateTurnStartButtons(sourceId)
        elif text == 'QUEEN':
            if getQueenOrderStatus(sourceId) == 'killed':
                line_bot_api.push_message(
                    sourceId,TextSendMessage(text='Queenは行動不能です\uD83D\uDE22'))
            elif getQueenOrderStatus(sourceId) == 'ordered':
                line_bot_api.push_message(
                    sourceId,TextSendMessage(text='Queenは行動済です\uD83D\uDE22'))
            else:
                setButtonStat(sourceId,'queen_wait_action')
                mainapp.generateTurnStartButtons(sourceId)
        elif num_matcher is None:
        #数字入力ではなかった
            line_bot_api.reply_message(
                reply_token,
                TextMessage(text='うまく認識できませんでした\uD83D\uDE22\nもう一度位置を入力してください。'))
        else:
            #数字→攻撃または移動先指定
            game_end = False
            if getKingOrderStatus(sourceId) == 'move_position_wait':
                current_position = getKingPosition(sourceId)
                if setKingPosition(sourceId,num_matcher.group(0)) == False:
                    line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には動けません\uD83D\uDCA6\n縦横方向で、Queenに重ならない場所を指定してください。'))
                else:
                    setKingOrderStatus(sourceId,'ordered')
                    clearNotHereList(sourceId)
                    setButtonStat(sourceId,'-')

            elif getQueenOrderStatus(sourceId) == 'move_position_wait':
                current_position = getQueenPosition(sourceId)
                if setQueenPosition(sourceId,num_matcher.group(0)) == False:
                    line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には動けません\uD83D\uDCA6\n縦横方向で、Kingに重ならない場所を指定してください。'))
                else:
                    setQueenOrderStatus(sourceId,'ordered')
                    clearNotHereList(sourceId)
                    setButtonStat(sourceId,'-')

            elif getKingOrderStatus(sourceId) == 'attack_position_wait' or getQueenOrderStatus(sourceId) == 'attack_position_wait':
                is_king_attack = False
                if getKingOrderStatus(sourceId) == 'attack_position_wait':
                    is_king_attack = True
                    current_position = getKingPosition(sourceId)
                else:
                    current_position = getQueenPosition(sourceId)

                if setAttackPosition(sourceId,current_position,num_matcher.group(0)) == False:
                    if is_king_attack == True:
                        line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には攻撃できません\uD83D\uDCA6\nあなたのKingの縦横斜めのお隣で、Queenが居ない場所を指定してください。'))
                    else:
                        line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には攻撃できません\uD83D\uDCA6\nあなたのQueenの縦横斜めのお隣で、Kingが居ない場所を指定してください。'))

                else:
                    setButtonStat(sourceId,'-')
                    impact_msg = getAttackImpact('com_'+sourceId,num_matcher.group(0))
                    addNotHereList(sourceId,num_matcher.group(0))

                    if impact_msg != u'':
                        if getKingOrderStatus('com_'+sourceId) == 'killed' and getQueenOrderStatus('com_'+sourceId) == 'killed':
                            #全滅させたので勝敗決定
                            clearHashData(sourceId)
                            game_end = True
                        else:
                            line_bot_api.push_message(sourceId,TextSendMessage(text='ワタシの'+impact_msg))
                    else:
                        line_bot_api.push_message(sourceId,TextSendMessage(text='かすりもしませんでした\uD83D\uDE12'))

                    if game_end != True:
                        if is_king_attack:
                            setKingOrderStatus(sourceId,'ordered')
                        else:
                            setQueenOrderStatus(sourceId,'ordered')
                    else:
                        return 'com_lose'

            if (getKingOrderStatus(sourceId) == 'ordered' or getKingOrderStatus(sourceId) == 'killed') and \
                (getQueenOrderStatus(sourceId) == 'ordered' or getQueenOrderStatus(sourceId) == 'killed'):

                if getKingOrderStatus(sourceId) == 'ordered':
                    setKingOrderStatus(sourceId,'notyet')
                if getQueenOrderStatus(sourceId) == 'ordered':
                    setQueenOrderStatus(sourceId,'notyet')

                setButtonStat(sourceId,'-')
                return 'com_turn'
            else:
                mainapp.generateTurnStartButtons(sourceId)
    return ''

def _createRound8List(current_position):
    if current_position == '1':
        return ['2','5','6']
    if current_position == '2':
        return ['1','3','5','6','7']
    if current_position == '3':
        return ['2','4','6','7','8']
    if current_position == '4':
        return ['3','7','8']
    if current_position == '5':
        return ['1','2','6','9','10']
    if current_position == '6':
        return ['1','2','3','5','7','9','10','11']
    if current_position == '7':
        return ['2','3','4','6','8','10','11','12']
    if current_position == '8':
        return ['3','4','7','11','12']
    if current_position == '9':
        return ['5','6','10','13','14']
    if current_position == '10':
        return ['5','6','7','9','11','13','14','15']
    if current_position == '11':
        return ['6','7','8','10','12','14','15','16']
    if current_position == '12':
        return ['7','8','11','15','16']
    if current_position == '13':
        return ['9','10','14']
    if current_position == '14':
        return ['9','10','11','13','15']
    if current_position == '15':
        return ['10','11','12','14','16']
    if current_position == '16':
        return ['11','12','15']

def _getAttackablePosition(sourceId,king_position,queen_position):
    at_list = _createRound8List(king_position)

    choice_list = []
    for choice_pos in at_list:
        if choice_pos != queen_position and notInClearedList(sourceId,choice_pos):
            choice_list.append(choice_pos)

    if len(choice_list) == 0:
        return '-'
    else:
        sampled_list = sample(choice_list,1)
        return str(sampled_list[0])

def _isComWin(sourceId,attack_pos):

    line_bot_api.push_message(sourceId,TextSendMessage(text=attack_pos+ u'に攻撃します\u2755'))
    impact_msg = getAttackImpact(sourceId,attack_pos)

    if impact_msg != u'':
        line_bot_api.push_message(sourceId,TextSendMessage(text=u'あなたの'+impact_msg))
        if getKingPosition(sourceId) != attack_pos:
            addNotHereList(sourceId,attack_pos)
        else:
            pass #命中したがKingがHP残り1なのでNotHereリストには入れない

        if getKingOrderStatus(sourceId) == 'killed' and getQueenOrderStatus(sourceId) == 'killed':
            return True
        else:
            return False
    else:
        addNotHereList(sourceId,attack_pos)
        return False

def _createMovableList(current_position):
    if current_position == '1':
        return ['5','9','13','2','3','4']
    if current_position == '2':
        return ['1','3','4','6','10','14']
    if current_position == '3':
        return ['1','2','4','11','7','15']
    if current_position == '4':
        return ['1','2','3','12','8','16']
    if current_position == '5':
        return ['1','7','6','8','9','13']
    if current_position == '6':
        return ['2','8','5','7','10','14']
    if current_position == '7':
        return ['3','5','6','8','11','15']
    if current_position == '8':
        return ['5','4','6','7','16','12']
    if current_position == '9':
        return ['1','5','11','10','13','12']
    if current_position == '10':
        return ['2','6','9','11','12','14']
    if current_position == '11':
        return ['3','7','9','10','12','15']
    if current_position == '12':
        return ['4','8','9','10','11','16']
    if current_position == '13':
        return ['1','5','9','14','15','16']
    if current_position == '14':
        return ['2','6','10','16','13','15']
    if current_position == '15':
        return ['3','7','11','13','14','16']
    if current_position == '16':
        return ['4','8','13','14','12','15']

def comAction(sourceId):
    king_position = getKingPosition('com_'+sourceId)
    queen_position = getQueenPosition('com_'+sourceId)

    if getKingOrderStatus('com_'+sourceId) != 'killed':
        attack_pos = _getAttackablePosition(sourceId,king_position,queen_position)
        if attack_pos != '-':
            if _isComWin(sourceId,attack_pos):
                return 'com_win'
        else:
            at_list = _createMovableList(king_position)
            two_list = sample(at_list,2)
            dist_pos = two_list[0]
            if setKingPosition('com_'+sourceId,dist_pos) == False:
                dist_pos = two_list[1]
                setKingPosition('com_'+sourceId,dist_pos)

            move_direction = getDistance(king_position,dist_pos,isKingDying('com_'+sourceId))
            msgtxt = u'Kingを' + unicode(move_direction,'utf-8')
            line_bot_api.push_message(sourceId,TextSendMessage(text=msgtxt))

    if getQueenOrderStatus('com_'+sourceId) != 'killed':
        attack_pos = _getAttackablePosition(sourceId,queen_position,king_position)
        if attack_pos != '-':
            if _isComWin(sourceId,attack_pos):
                return 'com_win'
        else:#move
            at_list = _createMovableList(queen_position)
            two_list = sample(at_list,2)
            dist_pos = two_list[0]
            if setQueenPosition('com_'+sourceId,dist_pos) == False:
                dist_pos = two_list[1]
                setQueenPosition('com_'+sourceId,dist_pos)

            move_direction = getDistance(queen_position,dist_pos,True)
            msgtxt = u'Queenを' + unicode(move_direction,'utf-8')
            line_bot_api.push_message(sourceId,TextSendMessage(text=msgtxt))

    return ''
