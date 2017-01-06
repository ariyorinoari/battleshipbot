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
from mutex import Mutex
from statdata import *

app = Flask(__name__)
app.config.from_object('config')
redis = redis.from_url(app.config['REDIS_URL'])
stream_handler = logging.StreamHandler()
app.logger.addHandler(stream_handler)
app.logger.setLevel(app.config['LOG_LEVEL'])
line_bot_api = LineBotApi(app.config['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['CHANNEL_SECRET'])
mapping = {"0":"0", "1":"1", "2":"2", "3":"3", "4":"5", "5":"8", "6":"13", "7":"20", "8":"40", "9":"?", "10":"∞", "11":"Soy"}

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
    filename = POKER_IMAGE_FILENAME.format(size)
    return send_from_directory(os.path.join(app.root_path, 'static', 'map'),
            filename)

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    #スタンプ対応
    sourceId = getSourceId(event.source)
    enemyId = getEnemyId(sourceId)
    if enemyId != '-':
        profile = line_bot_api.get_profile(sourceId)
        pack = event.message.package_id
        if pack == 1 or pack == 2 or pack ==3:
            line_bot_api.push_message(
                enemyId,
                StickerSendMessage(
                package_id=event.message.package_id,
                sticker_id=event.message.sticker_id))

@handler.add(FollowEvent)
def handle_follow(event):
#友達追加イベント、ここでredisへの登録を行う
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text='友達追加ありがとう\uD83D\uDE04\\n ゲームの始め方はボードメニューの中のヘルプで確認してね\uD83D\uDE03'))
    memberIdAdd(sourceId)
    memberNameAdd(profile.display_name,sourceId)
    createHashData(sourceId,profile.display_name,profile.picture_url)

@handler.add(UnfollowEvent)
def handle_unfollow(event):
#友達削除イベント、ここでredisからデータ削除を行う
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    memberIdRemove(sourceId)
    memberNameRemove(profile.display_name,sourceId)
    removeHashData(sourceId)

@handler.add(PostbackEvent)
def handle_postback(event):
#■ステータスbattle_quit_confirm(本当にやめますか？の確認ダイアログのポストバック）
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    answer = event.postback.data
    enemyId = getEnemyId(sourceId)

    if answer == 'QUIT_YES':
        #本当にやめますかのPostback　Yesなら相手に「降参」Pushし、ノーマル状態へ。
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='相手に降参メッセージを送って初期状態に戻ります。また遊んでね\uD83D\uDE09'))


        line_bot_api.push_message(
            enemyId,
            TextSendMessage(text=profile.display_name+'さんが降参しました\uD83D\uDE0F\n 初期状態に戻ります'))
        clearHashData(sourceId)
        clearHashData(enemyId)

    elif answer == 'QUIT_NO':
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='ゲームを続行します'))
    elif answer == 'GAME_END':
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='また遊んでね(ﾟ∇^*)'))
    else:
        #招待へのACK/REJECT対応
        matcher = re.match(r'(.*?)__(.*)', answer)
        if matcher is not None and matcher.group(1) == 'ACK':
            #誰かの招待受けて　Ack　の場合は、battle_init　状態へ、招待した側にAckメッセージ→battle_initへ。
            if isValidKey(matcher.group(2)):
                setStat(sourceId,'battle_init')
                if getEnemyId(sourceId) == '-':
                    setEnemy(sourceId,matcher.group(2))
                    line_bot_api.push_message(
                        matcher.group(2),generateAckMsg(profile.display_name,sourceId))
                #battle_initの最初はimagemap表示と、King位置入力を求めるメッセージを表示
                enemy_name = getEnemyName(matcher.group(2))
                line_bot_api.push_message(
                    sourceId,
                    TextSendMessage(text=enemy_name+'さんとのゲームを開始します。Kingの位置を決めてください。'))
                line_bot_api.push_message(
                    sourceId, generateInitialMap(sourceId))
        elif matcher is not None and matcher.group(1) == 'REJECT':
            #誰かの招待受けて　No　の場合は拒否を相手にPush
                if isValidKey(matcher.group(2)):
                    line_bot_api.push_message(
                        matcher.group(2),TextSendMessage(text=profile.display_name+'さんは今は無理なようです・・・\uD83D\uDE22'))
                    setEnemy(matcher.group(2),'-')
                    setStat(sourceId,'normal')

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
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
                TextMessage(text='ヘルプへようこそ\uD83D\uDE00\n 誰かと対戦したい場合は、対戦申込/やめる　を押してください。\n'+
                '対戦できる条件は２つ。①相手がXXとLINEでお友達になっていること。②相手のゲームキーがわかっていること。'))
            line_bot_api.push_message(
                sourceId,
                TextSendMessage(text='ちなみに'+profile.display_name+'さんのゲームキーはこれです！↓'))
            line_bot_api.push_message(
                sourceId,
                TextSendMessage(text=sourceId))
        elif matcher is not None and text.find('@') == 0:
            mention_matcher = re.match(r'@(.*)',matcher.group(1))
            if mention_matcher is not None:
                #@display_name__に続く文字列は相手にPushする・・・displayname重複対応がいりそう
                mentioned_key = getKeyFromDisplayName(mention_matcher.group(1))
                if mentioned_key is not None:
                    line_bot_api.push_message(
                    mentioned_key,
                    TextSendMessage(text=profile.display_name + 'さんからのメッセージ：\n'+ matcher.group(2)))
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='\uD83D\uDE32送信相手がわかりませんでした'))
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
                TextMessage(text='対戦を申し込むには、お相手のゲームキーが必要です。\n'+
                'ゲームキーは、ヘルプボタンを押すと表示されますのでお相手にお願いして教えてもらってくださいね。いったん対戦申込をキャンセルします\uD83D\uDE22'))
        else:
            #他テキストは相手キーとみなしてredis上に存在するか確認する
            if isValidKey(text):
                #ある場合は、相手ステータスを確認する。
                enemy_status = getStat(text)
                if enemy_status == 'normal':
                    #相手ステータスがノーマル状態であれば、招待ConfirmをPush
                    line_bot_api.push_message(
                        text,
                        generateInviteMsg(profile.display_name,sourceId))
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='キーの持ち主に対戦申込を送信しました\uD83D\uDE04'))
                    setStat(sourceId,'normal')
                    #この時点でenemy_keyを保持
                    setEnemy(sourceId,text)
                elif enemy_status == 'wait_game_key':
                    #相手がキーを入力しようとしている状態、相手ステータスをクリアした後invite
                    setStat(text,'normal')
                    line_bot_api.push_message(
                        text,
                        generateInviteMsg(profile.display_name,sourceId))
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='キーの持ち主に対戦申込を送信しました\uD83D\uDE04'))
                    setStat(sourceId,'normal')
                    #この時点でenemy_keyを保持
                    setEnemy(sourceId,text)
                else:
                    #相手は誰かと戦闘状態なのでメッセージPushのみ
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='キーの持ち主は誰かと対戦中なので今はダメですね・・\uD83D\uDE22\n 伝言だけしておきますね。初期状態に戻ります。'))
                    line_bot_api.push_message(
                        text,
                        TextSendMessage(text='おじゃまします。\n'+profile.display_name+'さんが対戦を希望していましたが、あとにしてもらいますね。'))
                    clearHashData(sourceId)
            else:
                #ない場合は、エラー表示し、再度相手キーを入力させる
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='キーが正しくないかもしれません\uD83D\uDE22\n 確認してもう一度入力してください'))

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
                TextMessage(text='マップ上の1から16の数字をタップして、位置を入力してくださいρ(-ω- ) '))
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
                            TextMessage(text='Kingを配置しました。\n 次はQueenの位置を入力してください'))
                elif getQueenPosition(sourceId) == '-':
                    if setQueenPosition(sourceId,num_matcher.group(0)) == False:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='うまく認識できませんでした\uD83D\uDE22\n マップ上の1から16の数字でQueenの位置を入力してください'))
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Queenを配置しました。'))
                if getKingPosition(sourceId) != '-' and getQueenPosition(sourceId) != '-':
                    #KingとQueenのPosition設定が決まったら、battle_readyステータス。
                    #本当はimagemap出したいが挫折
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
                            TextSendMessage(text='ゲーム開始、あなたのターンです。行動をメニューから選んでください。'))

#■ステータスbaattle_myturn
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
                'King,Queenのアクションをメニューから選んで場所を指定してくださいρ(-ω- )'))
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
                            TextMessage(text='Kingの移動先をタップしてください'))
                        setKingOrderStatus(sourceId,'move_position_wait')
                        if getQueenOrderStatus(sourceId) == 'move_position_wait' or getQueenOrderStatus(sourceId) == 'attack_position_wait':
                            setQueenOrderStatus(sourceId,'notyet')
                    elif matcher.group(2) == 'ATTACK':
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Kingの攻撃先をタップしてください'))
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
                            TextMessage(text='Queenの移動先をタップしてください'))
                        setQueenOrderStatus(sourceId,'move_position_wait')
                        if getKingOrderStatus(sourceId) == 'move_position_wait' or getKingOrderStatus(sourceId) == 'attack_position_wait':
                            setKingOrderStatus(sourceId,'notyet')
                    elif matcher.group(2) == 'ATTACK':
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='Queenの攻撃先をタップしてください'))
                        setQueenOrderStatus(sourceId,'attack_position_wait')
                        if getKingOrderStatus(sourceId) == 'move_position_wait' or getKingOrderStatus(sourceId) == 'attack_position_wait':
                            setKingOrderStatus(sourceId,'notyet')
            else:
                if text.find('@') == 0:
                #@開始→相手への通信
                    line_bot_api.push_message(
                        getEnemyId(sourceId),
                        TextSendMessage(text=profile.display_name + 'さんからのメッセージ：\n'+ matcher.group(2)))
                else:
                    num_matcher = re.match(r'^[0-9]{1,}$',text)
                    if num_matcher is None:
                        #数字入力ではなかった
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='うまく認識できませんでした\uD83D\uDE22\nもう一度位置を入力してください。\n'+
                            '相手にメッセージを送るには　@こんにちわ　のように@の後ろにメッセージをどうぞ'))
                    else:
                        game_end = False
                        if getKingOrderStatus(sourceId) == 'move_position_wait':
                            current_position = getKingPosition(sourceId)
                            if setKingPosition(sourceId,num_matcher.group(0)) == False:
                                line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には動けません'))
                            else:
                                move_direction = getDistance(current_position,num_matcher.group(0))
                                msgtxt = u'Kingが' + unicode(move_direction,'utf-8')
                                line_bot_api.push_message(getEnemyId(sourceId),TextSendMessage(text=msgtxt))
                                setKingOrderStatus(sourceId,'ordered')

                        elif getQueenOrderStatus(sourceId) == 'move_position_wait':
                            current_position = getQueenPosition(sourceId)
                            if setQueenPosition(sourceId,num_matcher.group(0)) == False:
                                line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には動けません'))
                            else:
                                move_direction = getDistance(current_position,num_matcher.group(0))
                                msgtxt = u'Queenが' + unicode(move_direction,'utf-8')
                                line_bot_api.push_message(getEnemyId(sourceId),TextSendMessage(text=msgtxt))
                                setQueenOrderStatus(sourceId,'ordered')

                        elif getKingOrderStatus(sourceId) == 'attack_position_wait' or getQueenOrderStatus(sourceId) == 'attack_position_wait':
                            is_king_attack = False
                            if getKingOrderStatus(sourceId) == 'attack_position_wait':
                                is_king_attack = True
                                current_position = getKingPosition(sourceId)
                            else:
                                current_position = getQueenPosition(sourceId)

                            if setAttackPosition(sourceId,current_position,num_matcher.group(0)) == False:
                                line_bot_api.push_message(sourceId,TextSendMessage(text='その位置には攻撃できません'))
                            else:
                                impact_msg = getAttackImpact(getEnemyId(sourceId),num_matcher.group(0))
                                msgtxt = num_matcher.group(0) + 'に攻撃されました。'
                                line_bot_api.push_message(getEnemyId(sourceId),TextSendMessage(text=msgtxt))

                                if unicode(impact_msg,'utf-8') != u'':
                                    if getKingOrderStatus(getEnemyId(sourceId)) == 'killed' and \
                                        getQueenOrderStatus(getEnemyId(sourceId)) == 'killed':
                                        #全滅させたので勝敗決定
                                        line_bot_api.push_message(sourceId,generateWinImage(profile.display_name,sourceId))
                                        clearHashData(sourceId)

                                        line_bot_api.push_message(getEnemyId(sourceId),generateLoseImage(getEnemyName(sourceId),getEnemyId(sourceId)))
                                        clearHashData(getEnemyId(sourceId))
                                        game_end = True
                                    else:
                                        line_bot_api.push_message(sourceId,TextSendMessage(text=impact_msg))
                                        line_bot_api.push_message(getEnemyId(sourceId),TextSendMessage(text=impact_msg))
                                else:
                                    line_bot_api.push_message(sourceId,TextSendMessage(text='かすりもしませんでした・・'))

                                if game_end != True:
                                    if is_king_attack:
                                        setKingOrderStatus(sourceId,'ordered')
                                    else:
                                        setQueenOrderStatus(sourceId,'ordered')

                        if game_end == True:
                            pass
                        elif (getKingOrderStatus(sourceId) == 'ordered' or getKingOrderStatus(sourceId) == 'killed') and \
                            (getQueenOrderStatus(sourceId) == 'ordered' or getQueenOrderStatus(sourceId) == 'killed'):
                            line_bot_api.push_message(sourceId,
                                TextSendMessage(text='相手のターンに移ります'))
                            line_bot_api.push_message(
                                getEnemyId(sourceId),
                                TextSendMessage(text='あなたのターンです。行動をメニューから選んでください。'))
                            #本当はimagemap出したいが挫折
                            line_bot_api.push_message(
                                getEnemyId(sourceId),
                                generateCurrentMap(getEnemyId(sourceId)))
                            setStat(sourceId,'battle_not_myturn')
                            setStat(getEnemyId(sourceId),'battle_myturn')
                            if getKingOrderStatus(sourceId) == 'ordered':
                                setKingOrderStatus(sourceId,'notyet')
                            if getQueenOrderStatus(sourceId) == 'ordered':
                                setQueenOrderStatus(sourceId,'notyet')
                        else:
                            line_bot_api.push_message(sourceId,TextSendMessage(text='次の行動をメニューから選んでください。'))

    elif currentStatus == 'battle_not_myturn':
        if text == 'ENTRY_EXIT_MENU':
            #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示
            line_bot_api.push_message(
                sourceId,generateQuitConfirm())
        elif text.find('@') == 0:
        #@つき→相手への通信
            line_bot_api.push_message(getEnemyId(sourceId),
                TextSendMessage(text=profile.display_name + 'さんからのメッセージ：\n'+ matcher.group(2)))
        else:
            line_bot_api.push_message(sourceId,
            TextSendMessage(text='相手のターンです。相手にメッセージを送るには　@こんにちわ　のように@の後ろにメッセージをどうぞ'))

def generateAckMsg(fromUserName,enemyId):
    confirm_template = ConfirmTemplate(
        title='対戦OK',
        text=fromUserName+'さんが対戦OKしました',
        actions=[
            PostbackTemplateAction(label='開始！', data='ACK__'+enemyId),
    ])
    template_message = TemplateSendMessage(
        alt_text='対戦OK', template=confirm_template)
    return template_message

def generateInviteMsg(fromUserName,fromUserId):
    #スペース抑制
    if fromUserName.find(' ') > 0:
        fromUserName = fromUserName.replace(' ','_')
    if fromUserName.find('　') > 0:
        fromUserName = fromUserName.replace('　','_')

    confirm_template = ConfirmTemplate(
        title='挑戦者',
        text=fromUserName+'さんからの対戦申し込みです',
        actions=[
            PostbackTemplateAction(label='うけて立つ', data='ACK__'+fromUserId),
            PostbackTemplateAction(label='あとで', data='REJECT__'+fromUserId)
    ])
    template_message = TemplateSendMessage(
        alt_text='対戦しよー', template=confirm_template)
    return template_message

def generateQuitConfirm():
    confirm_template = ConfirmTemplate(
        text='本当に対戦をやめますか？',
        actions=[
            PostbackTemplateAction(label='やめる', data='QUIT_YES'),
            PostbackTemplateAction(label='やめないで続ける', data='QUIT_NO')
    ])
    template_message = TemplateSendMessage(
        alt_text='かくにん', template=confirm_template)
    return template_message

def generateInitialMap(userId):
    message = ImagemapSendMessage(
            base_url='https://s-battleship.herokuapp.com/images/map',
        alt_text='battle field map',
        base_size=BaseSize(height=790, width=1040))
    actions=[]
    location=1
    for i in range(0, 4):
        for j in range(0, 4):
            actions.append(MessageImagemapAction(
                text = str(location).encode('utf-8'),
                area=ImagemapArea(
                    x=j * POKER_IMAGEMAP_ELEMENT_WIDTH,
                    y=i * POKER_IMAGEMAP_ELEMENT_HEIGHT,
                    width=(j + 1) * POKER_IMAGEMAP_ELEMENT_WIDTH,
                    height=(i + 1) * POKER_IMAGEMAP_ELEMENT_HEIGHT
                )
            ))
            location+=1
    message.actions = actions
    return message

#imagemapにしたいが挫折→通常イメージに仮変更したが、エラーで機能しない★★
def generateCurrentMap(userId):
    king_position = getKingPosition(userId)
    app.logger.info('[King Position] :' + king_position)
    queen_position = getQueenPosition(userId)
    app.logger.info('[Queen Position] :' + queen_position)
    number = generate_map_image(king_position,queen_position)
    #image_message = ImageSendMessage(
    #    original_content_url='https://s-battleship.herokuapp.com/images/tmp/'+tmp+'map.jpg',
    #    preview_image_url='https://s-battleship.herokuapp.com/images/tmp/'+tmp+'map.jpg')
    message = ImagemapSendMessage(
            base_url='https://s-battleship.herokuapp.com/images/tmp/' + number,
        alt_text='battle field map',
        base_size=BaseSize(height=790, width=1040))
    actions=[]
    location=1
    for i in range(0, 4):
        for j in range(0, 4):
            actions.append(MessageImagemapAction(
                text = str(location).encode('utf-8'),
                area=ImagemapArea(
                    x=j * POKER_IMAGEMAP_ELEMENT_WIDTH,
                    y=i * POKER_IMAGEMAP_ELEMENT_HEIGHT,
                    width=(j + 1) * POKER_IMAGEMAP_ELEMENT_WIDTH,
                    height=(i + 1) * POKER_IMAGEMAP_ELEMENT_HEIGHT
                )
            ))
            location+=1
    message.actions = actions
    return message

def generateWinImage(display_name,enemyId):
    buttons_template = ButtonsTemplate(
        title='You Win!',
        text=display_name+'さんの勝ち！',
        thumbnail_image_url='https://scrummasterbot.herokuapp.com/images/win.jpg',
        actions=[
            PostbackTemplateAction(label='もう１回', data='ACK__'+enemyId),
            PostbackTemplateAction(label='やめる', data='GAME_END'),
    ])
    template_message = TemplateSendMessage(
        alt_text='結果', template=buttons_template)
    return template_message

def generateLoseImage(display_name,enemyId):
    buttons_template = ButtonsTemplate(
        title='You Lose...',
        text=display_name+'さんの負け',
        thumbnail_image_url='https://scrummasterbot.herokuapp.com/images/lose.jpg',
        actions=[
            PostbackTemplateAction(label='もう１回', data='ACK__'+enemyId),
            PostbackTemplateAction(label='やめる', data='GAME_END'),
    ])
    template_message = TemplateSendMessage(
        alt_text='結果', template=buttons_template)
    return template_message

def genenate_voting_result_message(key):
    data = redis.hgetall(key)
    tmp = generate_voting_result_image(data)
    buttons_template = ButtonsTemplate(
        title='ポーカー結果',
        text='そろいましたか？',
        thumbnail_image_url='https://scrummasterbot.herokuapp.com/images/tmp/' + tmp + '/result_11.png',
        actions=[
            MessageTemplateAction(label='もう１回', text='プラポ')
    ])
    template_message = TemplateSendMessage(
        alt_text='結果', template=buttons_template)
    return template_message

def generate_planning_poker_message(number):
    message = ImagemapSendMessage(
        base_url='https://scrummasterbot.herokuapp.com/images/planning_poker',
        alt_text='planning poker',
        base_size=BaseSize(height=790, width=1040))
    actions=[]
    location=0
    for i in range(0, 3):
        for j in range(0, 4):
            actions.append(MessageImagemapAction(
                text = u'#' + number + u' ' + mapping[str(location).encode('utf-8')],
                area=ImagemapArea(
                    x=j * POKER_IMAGEMAP_ELEMENT_WIDTH,
                    y=i * POKER_IMAGEMAP_ELEMENT_HEIGHT,
                    width=(j + 1) * POKER_IMAGEMAP_ELEMENT_WIDTH,
                    height=(i + 1) * POKER_IMAGEMAP_ELEMENT_HEIGHT
                )
            ))
            location+=1
    message.actions = actions
    return message
