#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import errno
import logging
import os
import re
import redis
import time

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

from const import *
from utility import *
from statdata import *
from commode import *

app = Flask(__name__)
app.config.from_object('config')
redis = redis.from_url(app.config['REDIS_URL'])
stream_handler = logging.StreamHandler()
app.logger.addHandler(stream_handler)
app.logger.setLevel(app.config['LOG_LEVEL'])
line_bot_api = LineBotApi(app.config['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['CHANNEL_SECRET'])

@app.route('/callback', methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info('Request body: ' + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@app.route('/images/tmp/<number>/<size>', methods=['GET'])
def download_current(number, size):
    filename = 'map-' + size + '.png'
    return send_from_directory(os.path.join(app.root_path, 'static', 'tmp', number), filename)

@app.route('/images/map/<size>', methods=['GET'])
def download_imagemap(size):
    filename = FIELD_IMAGE_FILENAME.format(size)
    return send_from_directory(os.path.join(app.root_path, 'static', 'map'),
            filename)

@app.route('/images/kqbutton/<size>', methods=['GET'])
def download_imagekq(size):
    filename = KQ_IMAGE_FILENAME.format(size)
    return send_from_directory(os.path.join(app.root_path, 'static', 'kqbutton'),
            filename)

@app.route('/images/ambutton/<size>', methods=['GET'])
def download_imageam(size):
    filename = AM_IMAGE_FILENAME.format(size)
    return send_from_directory(os.path.join(app.root_path, 'static', 'ambutton'),
            filename)

@app.route('/images/<filename>', methods=['GET'])
def download_staticimage(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'),
            filename)

@handler.add(FollowEvent)
def handle_follow(event):
#友達追加イベント、ここでredisへの登録を行う
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    display_name = getUtfName(profile)

    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text='友達追加ありがとう\uD83D\uDE04\n'+
        '相手の持ち駒（King：耐久力2　と　Queen：耐久力1）をやっつけたら勝ち！の対戦ゲームです。詳しくはココ→　'+
        'http://yb300k.hateblo.jp/entry/2017/01/05/234756#rule \nゲームの始め方はボードメニューの中のヘルプで確認してね\uD83D\uDE03'))
    game_key = memberIdAdd(sourceId)

    line_bot_api.push_message(
        sourceId, TextSendMessage(text='あなたのゲームキーはこちら\u2755わからなくなったらヘルプで確認できます。↓'))
    line_bot_api.push_message(
        sourceId, TextSendMessage(text=game_key))
    createHashData(sourceId,display_name,game_key)
    setStat(sourceId,'wait_game_key')
    line_bot_api.push_message(
        sourceId,generateTutorialConfirm())

@handler.add(UnfollowEvent)
def handle_unfollow(event):
#友達削除イベント、ここでredisからデータ削除を行う
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    memberIdRemove(sourceId,getGameKey(sourceId))
    removeHashData(sourceId)

def getUtfName(profile):
    if isinstance(profile.display_name,str):
        return profile.display_name.decode('utf-8')
    else:
        return profile.display_name

@handler.add(PostbackEvent)
def handle_postback(event):
#■ステータスbattle_quit_confirm(本当にやめますか？の確認ダイアログのポストバック）
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    display_name = getUtfName(profile)
    answer = event.postback.data
    enemyId = getEnemyId(sourceId)

    if answer == 'QUIT_YES':
        #本当にやめますかのPostback　Yesなら相手に「降参」Pushし、ノーマル状態へ。
        if enemyId != '-':
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=u'相手に降参メッセージを送って初期状態に戻ります。また遊んでね\uD83D\uDE09'))

            line_bot_api.push_message(
                enemyId,
                TextSendMessage(text=display_name+u'さんが降参しました\uD83D\uDE0F\n 初期状態に戻ります'))
            clearHashData(enemyId)
            clearHashData(sourceId)
        else:
            if getStat(sourceId) == 'com_init' or getStat(sourceId) == 'com_battle':
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=u'私との対戦を終了して初期状態に戻ります\uD83D\uDE09'))
                clearHashData(sourceId)
                clearNotHereList(sourceId)
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=u'ゲームはすでに終わっているようです'))

    elif answer == 'QUIT_NO':
        if getStat(sourceId) != 'normal':
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text='ゲームを続行します'))
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text='ゲームはすでに終わっているようです'))

    elif answer == 'GAME_END':
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='また遊んでね\uD83D\uDE09'))
    else:
        #招待へのACK/REJECT対応
        matcher = re.match(r'(.*?)__(.*)', answer)
        if matcher is not None and matcher.group(1) == 'ACK':
            #誰かの招待受けて　Ack　の場合は、battle_init　状態へ、招待した側にAckメッセージ→battle_initへ。
            if isValidKey(matcher.group(2)):
                enemyId = getSourceIdfromGK(matcher.group(2))
                setStat(sourceId,'battle_init')
                if getEnemyId(sourceId) == '-':
                    setEnemy(sourceId,enemyId)
                    line_bot_api.push_message(
                        enemyId, generateAckMsg(display_name,sourceId))
                #battle_initの最初はimagemap表示と、King位置入力を求めるメッセージを表示
                enemy_name =getDisplayName(enemyId)
                if isinstance(enemy_name,str):
                    enemy_name = enemy_name.decode('utf-8')
                line_bot_api.push_message(
                    sourceId,
                    TextSendMessage(text=enemy_name+u'さんとのゲームを開始します。Kingの位置を決めてください。'))
                line_bot_api.push_message(
                    sourceId, generateInitialMap(sourceId))
        elif matcher is not None and matcher.group(1) == 'REJECT':
            #誰かの招待受けて　No　の場合は拒否を相手にPush
            if isValidKey(matcher.group(2)):
                enemyId = getSourceIdfromGK(matcher.group(2))
                line_bot_api.push_message(
                    enemyId,TextSendMessage(text=display_name+u'さんは今は無理なようです・・・\uD83D\uDE22'))
                if getStat(enemyId) == 'normal':
                    #相手側が招待済状態でこちらが拒否
                    setEnemy(enemyId,'-')
                setStat(sourceId,'normal')
        elif matcher is not None and matcher.group(1) == 'RESTART':
            #リベンジ申込
            if isValidKey(matcher.group(2)):
                enemyId = getSourceIdfromGK(matcher.group(2))
                enemy_status = getStat(enemyId)
                if enemy_status == 'normal':
                    #相手ステータスがノーマル状態であれば、招待メッセージをPush
                    line_bot_api.push_message(
                        enemyId,
                        generateInviteMsg(display_name,sourceId))
                else:
                    #相手は誰かと戦闘状態なのでメッセージPushのみ
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text=u'相手はすでに他の対戦に入ったようです・・\uD83D\uDE22\n 伝言だけしておきますね。'))
                    my_game_key = getGameKey(sourceId)
                    line_bot_api.push_message(
                        enemyId,
                        TextSendMessage(text=u'おじゃまします。\n'+display_name+u'さん('+ my_game_key +
                        ')が再戦を希望していましたが、あとにしてもらいますね。'))
                    clearHashData(sourceId)

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    display_name = getUtfName(profile)
    matcher = re.match(r'(.*?)__(.*)', text)
    currentStatus = getStat(sourceId)

#■ステータスノーマル（非戦闘状態）
    if currentStatus == 'normal':
        if text == 'ENTRY_EXIT_MENU':
            #対戦申込/やめる　ボタンの場合は相手キー入力待ち状態へ
            setStat(sourceId,'wait_game_key')
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='対戦相手のゲームキーを入力してください\uD83D\uDE00'))
        elif text == 'HELP_MENU':
            #ヘルプボタンの場合はゲーム説明の表示
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='ようこそ\uD83D\uDE00\n 対戦したい場合は、対戦申込/やめる を押してください。\n'+
                'その後相手のゲームキーを入力します。私と対戦するなら 1000 です。'))
            line_bot_api.push_message(
                sourceId,
                TextSendMessage(text='ちなみに'+display_name+'さんのゲームキーはこれです\u2755↓'))
            line_bot_api.push_message(
                sourceId,
                TextSendMessage(text=getGameKey(sourceId)))
            line_bot_api.push_message(
                sourceId,
                TextSendMessage(text='ゲームのルールはこちら http://yb300k.hateblo.jp/entry/2017/01/05/234756#rule'))

        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='\uD83D\uDC40もう一度お願いします'))

#■ステータス相手キー入力待ち
    elif currentStatus == 'wait_game_key':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合はノーマル状態へ
            clearHashData(sourceId)
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='対戦申込をキャンセルします。'))
        elif text == 'HELP_MENU':
        #ヘルプボタンの場合は招待方法を表示しノーマル状態へ
            clearHashData(sourceId)
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='対戦を申し込むには、相手のゲームキーが必要です。\n'+
                'ゲームキーは、ヘルプボタンで表示されるので相手に教えてもらってくださいね。いったん対戦申込をキャンセルします\uD83D\uDE22'))
        elif text == 'TUTO_NO':
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='では、困ったらヘルプかWebを見てね。よろしくお願いします\uD83D\uDE09'))
            setStat(sourceId,'normal')
        else:
            if text == '1000':#COMモード
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='では私が相手します\uD83D\uDE04やめたいときは対戦申込/やめるを押してください'))
                setStat(sourceId,'com_init')
                createComData(sourceId)
                line_bot_api.push_message(
                    sourceId, generateInitialMap(sourceId))
                line_bot_api.push_message(
                    sourceId, TextSendMessage(text=u'Kingの位置をどうぞ。'))

            #他テキストは相手キーとみなしてredis上に存在するか確認する
            elif isValidKey(text):
                #ある場合は、相手ステータスを確認する。
                enemyId = getSourceIdfromGK(text)
                enemy_status = getStat(enemyId)
                if enemy_status == 'normal':
                    #相手ステータスがノーマル状態であれば、招待メッセージをPush
                    line_bot_api.push_message(
                        enemyId,
                        generateInviteMsg(display_name,sourceId))
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='キーの持ち主に対戦申込を送りました\uD83D\uDE04'))
                    setStat(sourceId,'normal')
                    #この時点でenemy_keyを保持
                    setEnemy(sourceId,enemyId)
                elif enemy_status == 'wait_game_key':
                    #相手がキーを入力しようとしている状態、相手ステータスをクリアした後invite
                    setStat(enemyId,'normal')
                    line_bot_api.push_message(
                        enemyId,
                        generateInviteMsg(display_name,sourceId))
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='キーの持ち主に対戦申込を送りました\uD83D\uDE04'))
                    setStat(sourceId,'normal')
                    #この時点でenemy_keyを保持
                    setEnemy(sourceId,enemyId)
                else:
                    #相手は誰かと戦闘状態なのでメッセージPushのみ
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='キーの持ち主は誰かと対戦中なので今はダメですね・・\uD83D\uDE22\n 伝言だけして初期状態に戻ります。'))
                    line_bot_api.push_message(
                        enemyId,
                        TextSendMessage(text=u'おじゃまします。\n'+display_name+u'さん('+ my_game_key +
                        ')が対戦を希望していましたが、あとにしてもらいますね。'))
                    clearHashData(sourceId)
            else:
                #ない場合は、エラー表示し、再度相手キーを入力させる
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='キーが正しくないかもしれません\uD83D\uDE22\n 確認してもう一度入力してください'))
    elif currentStatus == 'com_init':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示し、battle_quit_confirm状態へ
            line_bot_api.reply_message(
                event.reply_token,generateQuitConfirm())
        else:
            ret = isComInitComplete(sourceId,event.reply_token,text)
            if ret == 'complete':
                setStat(sourceId,'com_battle')
                line_bot_api.push_message(
                    sourceId, generateCurrentMap(sourceId))
                line_bot_api.push_message(
                    sourceId, TextSendMessage(text=u'ではあなたのターン。KingかQueen、どちらに指示しますか\uD83D\uDE04'))
                generateTurnStartButtons(sourceId)
            elif ret == 'halfway':
                line_bot_api.push_message(
                    sourceId, TextSendMessage(text=u'Queenの位置をどうぞ。'))
    elif currentStatus == 'com_battle':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示
            line_bot_api.reply_message(
                event.reply_token,generateQuitConfirm())
        elif text == 'HELP_MENU':
            #ヘルプボタンの場合は配置方法を表示
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='私と対戦中です。\n '+
                    u'やめたいときには 対戦申込/やめる を押してください \uD83D\uDE04'))
        elif text == 'マップ':
            line_bot_api.reply_message(
                event.reply_token, generateCurrentMap(sourceId))
            line_bot_api.push_message(
                sourceId, TextSendMessage(text=u'マップを表示しました。行動または場所をどうぞ\uD83D\uDE04'))
        else:
            ret = comBattleUserInput(sourceId,event.reply_token,text)
            if ret == 'com_turn':
                line_bot_api.push_message(
                    sourceId, generateCurrentMap(sourceId))
                line_bot_api.push_message(sourceId,
                    TextMessage(text='ではこちらのターンです'))
                ###人工無能
                if comAction(sourceId) == 'com_win':
                    line_bot_api.push_message(
                        sourceId, TextSendMessage(text=u'私の勝ちです\uD83D\uDE04 リベンジはゲームキー1000で待ってます\uD83D\uDE00'))
                    clearHashData(sourceId)
                    clearNotHereList(sourceId)
                else:
                    line_bot_api.push_message(
                        sourceId, TextSendMessage(text=u'\uD83C\uDF1Fあなたのターン\uD83C\uDF1F'))
                    generateTurnStartButtons(sourceId)
            elif ret == 'com_lose':
                line_bot_api.reply_message(event.reply_token,
                    TextMessage(text=u'まいりました・・\uD83D\uDE22 もう1回やるならゲームキー1000で対戦申込ください。'))
                clearHashData(sourceId)
                clearNotHereList(sourceId)

#■ステータスbattle_init
    elif currentStatus == 'battle_init':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示し、battle_quit_confirm状態へ
            line_bot_api.push_message(
                sourceId,generateQuitConfirm())
        elif text == 'HELP_MENU':
            #ヘルプボタンの場合は配置方法を表示
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='マップ上の1から16の数字をタップして、位置を入力してください\uD83D\uDE04 '))
        else:
            num_matcher = re.match(r'^[0-9]{1,}$',text)
            if num_matcher is None:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='うまく認識できませんでした\uD83D\uDE22\n マップ上の1から16の数字をタップして、再度位置を入力してください'))
            else:
                if getKingPosition(sourceId) == '-':
                    if setKingPosition(sourceId,num_matcher.group(0)) == False:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='うまく認識できませんでした\uD83D\uDE22\n マップ上の1から16の数字でKingの位置を入力してください'))
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Kingを配置しました。\n 次はQueenの位置をどうぞ'))
                elif getQueenPosition(sourceId) == '-':
                    if setQueenPosition(sourceId,num_matcher.group(0)) == False:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='うまく認識できませんでした\uD83D\uDE22\n マップ上の1から16の数字でQueenの位置を入力してください。Kingと同じ場所はダメですよ。'))
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Queenを配置しました。'))
                if getKingPosition(sourceId) != '-' and getQueenPosition(sourceId) != '-':
                    #KingとQueenのPosition設定が決まったら、battle_readyステータス。
                    line_bot_api.push_message(
                        sourceId, generateCurrentMap(sourceId))
                    setStat(sourceId,'battle_ready')
                    enemyId = getEnemyId(sourceId)
                    if getStat(enemyId) != 'battle_ready':
                        #相手の場所設定が終わっていない
                        line_bot_api.push_message(
                            sourceId,
                            TextSendMessage(text='相手が配置を決め終わるまでお待ちください'))
                        #★★ここで待ち続けると抜けられなくなるので、一定時間でnormalに戻りたい
                    else:
                        #相手側はすでに完了していた
                        line_bot_api.push_message(
                            sourceId,
                            TextSendMessage(text='準備完了、相手のターンから開始します\uD83D\uDE04'))
                        setStat(sourceId,'battle_not_myturn')
                        setStat(enemyId,'battle_myturn')
                        #相手に開始＆入力求めるメッセージPush
                        line_bot_api.push_message(
                            enemyId,
                            TextSendMessage(text='ゲーム開始、あなたのターンです。KingかQueen、どちらに指示しますか\u2754'))
                        generateTurnStartButtons(enemyId)

#■ステータスbattle_ready
    elif currentStatus == 'battle_ready':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示
            line_bot_api.push_message(
                sourceId,generateQuitConfirm())
        elif text == 'HELP_MENU':
            #ヘルプボタンの場合は配置方法を表示
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text=getEnemyName(sourceId)+'さんと対戦中、相手の初期配置待ちです。\n '+
                '相手に話しかけるには、@まだー？のように、@の後ろにメッセージをどうぞ\uD83D\uDE04'))
#■ステータスbattle_myturn
    elif currentStatus == 'battle_myturn':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示
            line_bot_api.push_message(
                sourceId,generateQuitConfirm())
        elif text == 'HELP_MENU':
            #ヘルプボタンの場合は配置方法を表示
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text=getEnemyName(sourceId)+'さんと対戦中、あなたのターンです。\n '+
                'King,Queenの行動をボタンかボードメニューから選んで場所を指定してください\uD83D\uDE04'))
        else:
            if matcher is not None and matcher.group(1) == 'KING':
                if getKingOrderStatus(sourceId) == 'ordered':
                    line_bot_api.reply_message(event.reply_token,
                        TextMessage(text='\uD83D\uDE22Kingはすでに行動済です'))
                elif getKingOrderStatus(sourceId) == 'killed':
                    line_bot_api.reply_message(event.reply_token,
                        TextMessage(text='Kingは行動不能です\uD83D\uDE22'))
                else:
                    if matcher.group(2) == 'MOVE':
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Kingの移動先は\u2754'))
                        setKingOrderStatus(sourceId,'move_position_wait')
                        if getQueenOrderStatus(sourceId) == 'move_position_wait' or getQueenOrderStatus(sourceId) == 'attack_position_wait':
                            setQueenOrderStatus(sourceId,'notyet')
                    elif matcher.group(2) == 'ATTACK':
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Kingの攻撃先は\u2754'))
                        setKingOrderStatus(sourceId,'attack_position_wait')
                        if getQueenOrderStatus(sourceId) == 'move_position_wait' or getQueenOrderStatus(sourceId) == 'attack_position_wait':
                            setQueenOrderStatus(sourceId,'notyet')
            elif matcher is not None and matcher.group(1) == 'QUEEN':
                if getQueenOrderStatus(sourceId) == 'ordered':
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='\uD83D\uDE22Queenはすでに行動済です'))
                elif getQueenOrderStatus(sourceId) == 'killed':
                    line_bot_api.reply_message(event.reply_token,
                        TextMessage(text='Queenは行動不能です\uD83D\uDE22'))
                else:
                    if matcher.group(2) == 'MOVE':
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Queenの移動先は\u2754'))
                        setQueenOrderStatus(sourceId,'move_position_wait')
                        if getKingOrderStatus(sourceId) == 'move_position_wait' or getKingOrderStatus(sourceId) == 'attack_position_wait':
                            setKingOrderStatus(sourceId,'notyet')
                    elif matcher.group(2) == 'ATTACK':
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Queenの攻撃先は\u2754'))
                        setQueenOrderStatus(sourceId,'attack_position_wait')
                        if getKingOrderStatus(sourceId) == 'move_position_wait' or getKingOrderStatus(sourceId) == 'attack_position_wait':
                            setKingOrderStatus(sourceId,'notyet')
            else:
                enemyId = getEnemyId(sourceId)
                if text == 'マップ':
                    line_bot_api.push_message(
                        sourceId, generateCurrentMap(sourceId))
                elif text == 'KING':
                    setKingOrderStatus(sourceId,'wait_action')
                    generateTurnStartButtons(sourceId)
                elif text == 'QUEEN':
                    setQueenOrderStatus(sourceId,'wait_action')
                    generateTurnStartButtons(sourceId)
                elif text.find('@') == 0:
                #@開始→相手への通信
                    line_bot_api.push_message(
                        enemyId,TextSendMessage(text=display_name + 'さんからのメッセージ：\n'+ text[1:]))
                else:
                    num_matcher = re.match(r'^[0-9]{1,}$',text)
                    if num_matcher is None:
                        #数字入力ではなかった
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='うまく認識できませんでした\uD83D\uDE22\nもう一度位置を入力してください。\n'+
                            '相手にメッセージを送るには　@こんにちわ　のように@の後ろにメッセージをどうぞ'))
                    else:
                        #数字→攻撃または移動先指定
                        game_end = False
                        if getKingOrderStatus(sourceId) == 'move_position_wait':
                            current_position = getKingPosition(sourceId)
                            if setKingPosition(sourceId,num_matcher.group(0)) == False:
                                line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には動けません\uD83D\uDCA6\n縦横方向で、Queenに重ならない場所を指定してください。'))
                            else:
                                move_direction = getDistance(current_position,num_matcher.group(0),isKingDying(sourceId))
                                msgtxt = u'Kingが' + unicode(move_direction,'utf-8')
                                line_bot_api.push_message(enemyId,TextSendMessage(text=msgtxt))
                                setKingOrderStatus(sourceId,'ordered')

                        elif getQueenOrderStatus(sourceId) == 'move_position_wait':
                            current_position = getQueenPosition(sourceId)
                            if setQueenPosition(sourceId,num_matcher.group(0)) == False:
                                line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には動けません\uD83D\uDCA6\n縦横方向で、Kingに重ならない場所を指定してください。'))
                            else:
                                move_direction = getDistance(current_position,num_matcher.group(0),True)
                                msgtxt = u'Queenが' + unicode(move_direction,'utf-8')
                                line_bot_api.push_message(enemyId,TextSendMessage(text=msgtxt))
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
                                impact_msg = getAttackImpact(enemyId,num_matcher.group(0))
                                line_bot_api.push_message(enemyId,TextSendMessage(text=num_matcher.group(0) + u'に攻撃あり\u2755'))

                                if impact_msg != u'':
                                    if getKingOrderStatus(enemyId) == 'killed' and getQueenOrderStatus(enemyId) == 'killed':
                                        #全滅させたので勝敗決定
                                        line_bot_api.push_message(enemyId,generateLoseImage(getEnemyName(sourceId),sourceId))
                                        clearHashData(enemyId)

                                        line_bot_api.push_message(sourceId,generateWinImage(display_name,enemyId))
                                        clearHashData(sourceId)
                                        game_end = True
                                    else:
                                        line_bot_api.push_message(sourceId,TextSendMessage(text=impact_msg))
                                        line_bot_api.push_message(enemyId,TextSendMessage(text=impact_msg))
                                else:
                                    line_bot_api.push_message(sourceId,TextSendMessage(text='かすりもしませんでした\uD83D\uDE12'))

                                if game_end != True:
                                    if is_king_attack:
                                        setKingOrderStatus(sourceId,'ordered')
                                    else:
                                        setQueenOrderStatus(sourceId,'ordered')

                        if game_end == True:
                            pass
                        elif (getKingOrderStatus(sourceId) == 'ordered' or getKingOrderStatus(sourceId) == 'killed') and \
                            (getQueenOrderStatus(sourceId) == 'ordered' or getQueenOrderStatus(sourceId) == 'killed'):
                            line_bot_api.push_message(
                                sourceId, generateCurrentMap(sourceId))
                            line_bot_api.push_message(sourceId,
                                TextSendMessage(text='－－相手のターン－－'))
                            line_bot_api.push_message(
                                enemyId,TextSendMessage(text='\uD83C\uDF1Fあなたのターン\uD83C\uDF1F'))
                            setStat(sourceId,'battle_not_myturn')
                            setStat(enemyId,'battle_myturn')
                            generateTurnStartButtons(enemyId)

                            if getKingOrderStatus(sourceId) == 'ordered':
                                setKingOrderStatus(sourceId,'notyet')
                            if getQueenOrderStatus(sourceId) == 'ordered':
                                setQueenOrderStatus(sourceId,'notyet')
                        else:
                            line_bot_api.push_message(sourceId,TextSendMessage(text='次の行動は\u2754'))

    elif currentStatus == 'battle_not_myturn':
        if text == 'ENTRY_EXIT_MENU':
            #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示
            line_bot_api.push_message(
                sourceId,generateQuitConfirm())
        elif text == 'HELP_MENU':
            line_bot_api.reply_message(event.reply_token,
                TextMessage(text=getEnemyName(sourceId)+'さんと対戦中、相手のターンです。'))

        elif text.find('@') == 0:
        #@つき→相手への通信
            line_bot_api.push_message(getEnemyId(sourceId),
                TextSendMessage(text=display_name + 'さんからのメッセージ：\n'+ text[1:]))
        else:
            line_bot_api.push_message(sourceId,
                TextSendMessage(text='相手のターンです。相手にメッセージを送るには　@こんにちわ　のように@の後ろにメッセージをどうぞ'))

def generateTurnStartButtons(sourceId):

    if getQueenOrderStatus(sourceId) == 'wait_action' or getKingOrderStatus(sourceId) == 'ordered' or getKingOrderStatus(sourceId) == 'killed':
        line_bot_api.push_message(sourceId,TextSendMessage(text='Queenの行動を選んでください'))
        line_bot_api.push_message(sourceId,generateAMbuttons('QUEEN__'))
    elif getKingOrderStatus(sourceId) == 'wait_action' or getQueenOrderStatus(sourceId) == 'ordered' or getQueenOrderStatus(sourceId) == 'killed':
        line_bot_api.push_message(sourceId,TextSendMessage(text='Kingの行動を選んでください'))
        line_bot_api.push_message(sourceId,generateAMbuttons('KING__'))
    else:
        line_bot_api.push_message(sourceId,TextSendMessage(text='KingとQueen、どちらに指示しますか\u2754'))
        line_bot_api.push_message(sourceId,generateKQbuttons())

def generateAMbuttons(character):
    message = ImagemapSendMessage(
        base_url= HEROKU_SERVER_URL + 'images/ambutton',
        alt_text='attack or move',
        base_size=BaseSize(height=178, width=1040))
    actions=[]
    actions.append(MessageImagemapAction(
        text = character + 'ATTACK',
        area=ImagemapArea(
            x=0,
            y=0,
            width = BUTTON_ELEMENT_WIDTH,
            height = BUTTON_ELEMENT_HEIGHT)))
    actions.append(MessageImagemapAction(
        text = character + 'MOVE',
        area=ImagemapArea(
            x=BUTTON_ELEMENT_WIDTH,
            y=BUTTON_ELEMENT_HEIGHT,
            width = BUTTON_ELEMENT_WIDTH * 2,
            height = BUTTON_ELEMENT_HEIGHT * 2)))
    message.actions = actions
    return message

def generateKQbuttons():
    message = ImagemapSendMessage(
        base_url= HEROKU_SERVER_URL + 'images/kqbutton',
        alt_text='king or queen',
        base_size=BaseSize(height=178, width=1040))
    actions=[]
    actions.append(MessageImagemapAction(
        text = 'KING',
        area=ImagemapArea(
            x=0,
            y=0,
            width = BUTTON_ELEMENT_WIDTH,
            height = BUTTON_ELEMENT_HEIGHT)))
    actions.append(MessageImagemapAction(
        text = 'QUEEN',
        area=ImagemapArea(
            x=BUTTON_ELEMENT_WIDTH,
            y=BUTTON_ELEMENT_HEIGHT,
            width = BUTTON_ELEMENT_WIDTH * 2,
            height = BUTTON_ELEMENT_HEIGHT * 2)))
    message.actions = actions
    return message

def generateAckMsg(fromUserName,enemyId):
    buttons_template = ButtonsTemplate(
        text=fromUserName+u'さんが対戦OKしました',
        actions=[
            PostbackTemplateAction(label=u'開始', data=u'ACK__'+getGameKey(enemyId))
    ])
    template_message = TemplateSendMessage(
        alt_text=u'対戦OK', template=buttons_template)
    return template_message

def generateInviteMsg(fromUserName,fromUserId):
    confirm_template = ConfirmTemplate(
        text=fromUserName+u'さんからの対戦申し込みです',
        actions=[
            PostbackTemplateAction(label='うけて立つ', data='ACK__'+getGameKey(fromUserId)),
            PostbackTemplateAction(label='あとで', data='REJECT__'+getGameKey(fromUserId))
    ])
    template_message = TemplateSendMessage(
        alt_text='対戦しよー', template=confirm_template)
    return template_message

def generateQuitConfirm():
    confirm_template = ConfirmTemplate(
        text=u'本当に対戦をやめますか\u2754',
        actions=[
            PostbackTemplateAction(label='やめる', data='QUIT_YES'),
            PostbackTemplateAction(label='やめないで続ける', data='QUIT_NO')
    ])
    template_message = TemplateSendMessage(
        alt_text='かくにん', template=confirm_template)
    return template_message

def generateTutorialConfirm():
    confirm_template = ConfirmTemplate(
        text=u'試しに私と対戦しますか\u2754',
        actions=[
            MessageTemplateAction(label=u'試す', text='1000'),
            MessageTemplateAction(label=u'遠慮します', text='TUTO_NO')
    ])
    template_message = TemplateSendMessage(
        alt_text='チュートリアル', template=confirm_template)
    return template_message


def generateInitialMap(userId):
    message = ImagemapSendMessage(
        base_url= HEROKU_SERVER_URL + 'images/map',
        alt_text='battle field map',
        base_size=BaseSize(height=790, width=1040))
    actions=[]
    location=1
    for i in range(0, 4):
        for j in range(0, 4):
            actions.append(MessageImagemapAction(
                text = str(location).encode('utf-8'),
                area=ImagemapArea(
                    x=j * IMAGEMAP_ELEMENT_WIDTH,
                    y=i * IMAGEMAP_ELEMENT_HEIGHT,
                    width=(j + 1) * IMAGEMAP_ELEMENT_WIDTH,
                    height=(i + 1) * IMAGEMAP_ELEMENT_HEIGHT
                )
            ))
            location+=1
    message.actions = actions
    return message

def generateCurrentMap(userId):
    king_position = getKingPosition(userId)
    app.logger.info('[King Position] :' + king_position)
    queen_position = getQueenPosition(userId)
    app.logger.info('[Queen Position] :' + queen_position)
    number = generate_map_image(king_position,queen_position)

    message = ImagemapSendMessage(
            base_url= HEROKU_SERVER_URL + 'images/tmp/' + number,
        alt_text='battle field map',
        base_size=BaseSize(height=790, width=1040))
    actions=[]
    location=1
    for i in range(0, 4):
        for j in range(0, 4):
            actions.append(MessageImagemapAction(
                text = str(location).encode('utf-8'),
                area=ImagemapArea(
                    x=j * IMAGEMAP_ELEMENT_WIDTH,
                    y=i * IMAGEMAP_ELEMENT_HEIGHT,
                    width=(j + 1) * IMAGEMAP_ELEMENT_WIDTH,
                    height=(i + 1) * IMAGEMAP_ELEMENT_HEIGHT
                )
            ))
            location+=1
    message.actions = actions
    return message

def generateWinImage(display_name,enemyId):
    buttons_template = ButtonsTemplate(
        text=display_name+u'さんの勝ち\u2755\uD83D\uDC4F',
        thumbnail_image_url=HEROKU_SERVER_URL + 'images/win3.jpg',
        actions=[
            PostbackTemplateAction(label='もう１回', data='RESTART__'+enemyId),
            PostbackTemplateAction(label='やめる', data='GAME_END'),
    ])
    template_message = TemplateSendMessage(
        alt_text='結果', template=buttons_template)
    return template_message

def generateLoseImage(display_name,enemyId):
    buttons_template = ButtonsTemplate(
        text=unicode(display_name,'utf-8')+u'さんの負けです\uD83D\uDE1E',
        thumbnail_image_url=HEROKU_SERVER_URL + 'images/lose3.jpg',
        actions=[
            PostbackTemplateAction(label='もう１回', data='RESTART__'+enemyId),
            PostbackTemplateAction(label='やめる', data='GAME_END'),
    ])
    template_message = TemplateSendMessage(
        alt_text='結果', template=buttons_template)
    return template_message
