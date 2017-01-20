#-*- coding: utf-8 -*-

from __future__ import unicode_literals

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

import re

from const import *
from utility import *
from statdata import *

def isComInitComplete(sourceId,reply_token,text):
    if text == 'ENTRY_EXIT_MENU':
    #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示し、battle_quit_confirm状態へ
        line_bot_api.reply_message(
            reply_token,generateQuitConfirm())
    else:
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
    if text == 'ENTRY_EXIT_MENU':
    #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示し、battle_quit_confirm状態へ
        line_bot_api.reply_message(
            reply_token,generateQuitConfirm())
        return ''
    elif text == 'HELP_MENU':
        #ヘルプボタンの場合は配置方法を表示
        line_bot_api.reply_message(
            reply_token,
            TextMessage(text='私と対戦中です。\n '+
            'やめたいときには 対戦申込/やめる を押してください\uD83D\uDE04'))
        return ''
    else:
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
            if num_matcher is None:
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

                elif getQueenOrderStatus(sourceId) == 'move_position_wait':
                    current_position = getQueenPosition(sourceId)
                    if setQueenPosition(sourceId,num_matcher.group(0)) == False:
                        line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には動けません\uD83D\uDCA6\n縦横方向で、Kingに重ならない場所を指定してください。'))
                    else:
                        setQueenOrderStatus(sourceId,'ordered')

                elif getKingOrderStatus(sourceId) == 'attack_position_wait' or getQueenOrderStatus(sourceId) == 'attack_position_wait':
                    is_king_attack = False
                    if getKingOrderStatus(sourceId) == 'attack_position_wait':
                        is_king_attack = True
                        current_position = getKingPosition(sourceId)
                    else:
                        current_position = getQueenPosition(sourceId)

                    if setAttackPosition(sourceId,current_position,num_matcher.group(0)) == False:
                        line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には攻撃できません\uD83D\uDCA6\n縦横斜めのお隣で、自軍のKing、Queenが居ない場所を指定してください。'))
                    else:
                        impact_msg = getAttackImpact('com_'+sourceId,num_matcher.group(0))

                        if impact_msg != u'':
                            if getKingOrderStatus('com_'+sourceId) == 'killed' and getQueenOrderStatus('com_'+sourceId) == 'killed':
                                #全滅させたので勝敗決定
                                clearHashData(sourceId)
                                game_end = True
                            else:
                                line_bot_api.push_message(sourceId,TextSendMessage(text=impact_msg))
                        else:
                            line_bot_api.push_message(sourceId,TextSendMessage(text='かすりもしませんでした\uD83D\uDE12'))

                        if game_end != True:
                            if is_king_attack:
                                setKingOrderStatus(sourceId,'ordered')
                            else:
                                setQueenOrderStatus(sourceId,'ordered')

                if game_end == True:
                    return 'com_lose'
                elif (getKingOrderStatus(sourceId) == 'ordered' or getKingOrderStatus(sourceId) == 'killed') and \
                    (getQueenOrderStatus(sourceId) == 'ordered' or getQueenOrderStatus(sourceId) == 'killed'):
                    line_bot_api.push_message(
                        sourceId, generateCurrentMap(sourceId))

                    if getKingOrderStatus(sourceId) == 'ordered':
                        setKingOrderStatus(sourceId,'notyet')
                    if getQueenOrderStatus(sourceId) == 'ordered':
                        setQueenOrderStatus(sourceId,'notyet')
                    return 'com_turn'
                else:
                    line_bot_api.push_message(sourceId,TextSendMessage(text='次の行動は\u2754'))
    return ''

def _createRound8List(current_position):
    if current_position = '1':
        return ['2','5','6']
    if current_position = '2':
        return ['1','3','5','6','7']
    if current_position = '3':
        return ['2','4','6','7','8']
    if current_position = '4':
        return ['3','7','8']
    if current_position = '5':
        return ['1','2','6','9','10']
    if current_position = '6':
        return ['1','2','3','5','7','9','10','11']
    if current_position = '7':
        return ['2','3','4','6','8','10','11','12']
    if current_position = '8':
        return ['3','4','7','11','12']
    if current_position = '9':
        return ['5','6','10','13','14']
    if current_position = '10':
        return ['5','6','7','9','11','13','14','15']
    if current_position = '11':
        return ['6','7','8','10','12','14','15','16']
    if current_position = '12':
        return ['7','8','11','15','16']
    if current_position = '13':
        return ['9','10','14']
    if current_position = '14':
        return ['9','10','11','13','15']
    if current_position = '15':
        return ['10','11','12','14','16']
    if current_position = '16':
        return ['11','12','15']

def _isComWin(sourceId,king_position,queen_position):
    at_list = _createRound8List(king_position)
    two_list = random.sample(at_list,2)
    if two_list[0] != queen_position:
        attack_pos = two_list[0]
    else:
        attack_pos = two_list[1]
    line_bot_api.push_message(sourceId,TextSendMessage(text=attack_pos+ u'に攻撃あり\u2755'))
    impact_msg = getAttackImpact(sourceId,attack_pos)

    if impact_msg != u'':
        if getKingOrderStatus(sourceId) == 'killed' and getQueenOrderStatus(sourceId) == 'killed':
            return True
        else:
            line_bot_api.push_message(sourceId,TextSendMessage(text=impact_msg))
    return False

def comAction(sourceId):
    king_position = getKingPosition('com_'+sourceId))
    queen_position = getQueenPosition('com_'+sourceId)

    if getKingOrderStatus('com_'+sourceId) != 'killed':
        if randint(1,2) == 1:#attack
            if _isComWin(sourceId,king_position,queen_position):
                return 'com_win'
        else:#move
            pass
    if getQueenOrderStatus('com_'+sourceId) != 'killed':
        if randint(1,2) == 1:#attack
            if _isComWin(sourceId,queen_position,king_position):
                return 'com_win'
        else:#move
            pass
    return ''
