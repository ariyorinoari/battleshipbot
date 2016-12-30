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
    UnfollowEvent, FollowEvent,
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

@app.route('/images/tmp/<number>/<filename>', methods=['GET'])
def download_result(number, filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'tmp', number), filename)

@app.route('/images/planning_poker/<size>', methods=['GET'])
def download_imagemap(size):
    filename = POKER_IMAGE_FILENAME.format(size)
    return send_from_directory(os.path.join(app.root_path, 'static', 'planning_poker'),
            filename)

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    #スタンプ対応
    sourceId = getSourceId(event.source)
    enemyId = getEnemyId(sourceId)
    if enemyId is not None:
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
        event.reply_token, TextSendMessage(text='友達追加ありがとう(ﾟ▽ﾟ*)\n ゲームの始め方はボードメニューの中のヘルプで確認してね(＾▽＾)'))
    memberIdAdd(sourceId)
    memberNameAdd(profile.display_name,sourceId)
    createHashData(sourceId,profile.display_name,profile.picture_url)

@handler.add(UnfollowEvent)
def handle_unfollow(event):
#友達削除イベント、ここでredisからデータ削除を行う
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text='･△･)ﾉ また友達になってね！'))
    memberIdRemove(sourceId)
    memberNameRemove(profile.display_name,sourceId)
    removeHashData(sourceId)

@handler.add(PostbackEvent)
def handle_postback(event):
#■ステータスbattle_quit_confirm(本当にやめますか？の確認ダイアログのポストバック）
    sourceId = getSourceId(event.source)
    profile = line_bot_api.get_profile(sourceId)
    answer = event.postback.data
    matcher = re.match(r'(.*?)__(.*)', text)

    enemyId = getEnemyId(sourceId)
    if answer == 'QUIT_YES':
        #Yesなら相手に「降参」Pushし、ノーマル状態へ。
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='相手に降参メッセージを送って初期状態に戻ります。また遊んでね(ﾟ∇^*)'))
        line_bot_api.push_message(
            enemyId,
            TextSendMessage(text=profile.display_name+'さんが降参しました(￣∇￣)初期状態に戻ります'))
        setStat(sourceId,'normal')
        setStat(enemyId,'normal')
        setEnemy(sourceId,'')
        setEnemy(enemyId,'')
    elif answer == 'QUIT_NO':
        #Noなら直前のステータスに戻る
        setStat(sourceId,getPreviousStat(sourceId))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='ゲームを続行します'))
    else:
        line_bot_api.push_message(
            sourceId,generateQuitConfirm())
        #他のメニュー押される可能性はいったん考慮しない

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
                TextMessage(text='対戦相手のゲームキーを入力してください(´▽｀)'))
        elif text == 'HELP_MENU':
            #ヘルプボタンの場合はゲーム説明の表示
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='ヘルプへようこそ(*^^*)\n 誰かと対戦したい場合は、対戦申込/やめる　を押してください。\n'+
                '対戦できる条件は２つ。①相手がXXとLINEでお友達になっていること。②相手のゲームキーがわかっていること。'))
            line_bot_api.push_message(
                sourceId,
                TextSendMessage(text='ちなみに'+profile.display_name+'さんのゲームキーはこれです！↓'))
            line_bot_api.push_message(
                sourceId,
                TextSendMessage(text=sourceId))
        elif matcher is not None and text.find('@') == 1:
            if matcher.group(1) == 'ACK':
                #誰かの招待受けて　Ack　の場合は、battle_init　状態へ、招待した側にAckメッセージ→battle_initへ。
                if isValidKey(matcher.group(2)):
                    setStat(sourceId,'battle_init')
                    if getEnemyId(sourceId) is None:
                        setEnemy(sourceId,matcher.group(2))
                        line_bot_api.push_message(
                            matcher.group(2),generateAckMsg(profile.display_name))
                    #battle_initの最初はimagemap表示と、King位置入力を求めるメッセージを表示
                    displayInitialMap()
                    enemy_name = getEnemyName(matcher.group(2))
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text=enemy_name+'さんとのゲームを開始します。Kingの位置を決めてください。'))
            elif matcher.group(1) == 'REJECT':
                #誰かの招待受けて　No　の場合は拒否を相手にPush
                if isValidKey(matcher.group(2)):
                    line_bot_api.push_message(
                        matcher.group(2),generateRejectMsg(profile.display_name))
                    setEnemy(matcher.group(2),'')
            else:
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
                        TextMessage(text='( ﾟﾛﾟ)送信相手がわかりませんでした'))
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='σ(￣、￣=)'))

#■ステータス相手キー入力待ち
    elif currentStatus == 'wait_game_key':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合はノーマル状態へ
            setStat(sourceId,'normal')
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='対戦申込をキャンセルします。'))
        elif text == 'HELP_MENU':
        #ヘルプボタンの場合は招待方法を表示しノーマル状態へ
            setStat(sourceId,'normal')
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text='対戦を申し込むには、お相手のゲームキーが必要です。\n'+
                'ゲームキーは、ヘルプボタンを押すと表示されますのでお相手にお願いして教えてもらってくださいね。いったん対戦申込をキャンセルします(-人-)'))
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
                        TextMessage(text='キーの持ち主に対戦申込を送信しました(^ー^* )'))
                    setStat(sourceId,'normal')
                    #この時点でenemy_keyを保持
                    setEnemyKey(sourceId,text)
                elif enemy_status == 'wait_game_key':
                    #相手がキーを入力しようとしている状態、相手ステータスをクリアした後invite
                    setStat(text,'normal')
                    line_bot_api.push_message(
                        text,
                        generateInviteMsg(profile.display_name,sourceId))
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='キーの持ち主に対戦申込を送信しました(^ー^* )'))
                    setStat(sourceId,'normal')
                    #この時点でenemy_keyを保持
                    setEnemyKey(sourceId,text)
                else:
                    #相手は誰かと戦闘状態なのでメッセージPushのみ
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text='キーの持ち主は誰かと対戦中なので今はダメですね・・(;д;)\n 伝言だけしておきますね。初期状態に戻ります。'))
                    line_bot_api.push_message(
                        text,
                        TextSendMessage(text='おじゃまします。\n'+profile.display_name+'さんが対戦を希望していましたが、あとにしてもらいますね。'))
                    setStat(sourceId,'normal')
            else:
                #ない場合は、エラー表示し、再度相手キーを入力させる
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='キーが正しくないかもしれません( ﾟﾛﾟ)\n 確認してもう一度入力してください'))

#■ステータスbattle_init
    elif currentStatus == 'battle_init':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示し、battle_quit_confirm状態へ
#            setPreviousStat(sourceId,'battle_init')
#            setStat(sourceId,'battle_quit_confirm')
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
                    TextMessage(text='うまく認識できませんでした( ﾟﾛﾟ)\n マップ上の1から16の数字をタップして、再度位置を入力してください'))
            else:
                if getKingPosition(sourceId) == '-':
                    if setKingPosition(sourceId,num_matcher(0)) == False:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='うまく認識できませんでした( ﾟﾛﾟ)\n マップ上の1から16の数字でKingの位置を入力してください'))
                elif getQueenPosition(sourceId) == '-':
                    if setQueenPosition(sourceId,num_matcher(0)) == False:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='うまく認識できませんでした( ﾟﾛﾟ)\n マップ上の1から16の数字でQueenの位置を入力してください'))
                if getKingPosition(sourceId) != '-' and getQueenPosition(sourceId) != '-':
                    #KingとQueenのPosition設定が決まったら、battle_readyステータス。
                    setStat(sourceId,'battle_ready')
                    enemyId = getEnemyId(sourceId)
                    if getStat(enemyId) != 'battle_ready':
                        #相手の場所設定が終わっていない
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='相手が配置を決め終わるまでお待ちください'))
                        #★★ここで待ち続けると抜けられなくなるので、一定時間でnormalに戻りたい
                    else:
                        #相手側はすでに完了していた
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextMessage(text='準備完了、相手のターンから開始します(^ー^* )'))
                        setStat(sourceId,'battle_not_myturn')
                        setStat(enemyId,'battle_myturn')
                        #相手に開始＆入力求めるメッセージPush
                        line_bot_api.push_message(
                            enemyId,
                            TextSendMessage(text='ゲーム開始、あなたのターンです。行動をメニューから選んでください。'))

#■ステータスbaattle_myturn
    elif currentStatus == 'battle_myturn':
        if text == 'ENTRY_EXIT_MENU':
        #対戦申込/やめる　ボタンの場合は本当にやめるかConfirm表示し、battle_quit_confirm状態へ
            setPreviousStat(sourceId,'battle_init')
            setStat(sourceId,'battle_quit_confirm')
            line_bot_api.push_message(
                sourceId,generateQuitConfirm())
        elif text == 'HELP_MENU':
            #ヘルプボタンの場合は配置方法を表示
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text=getEnemyName(sourceId)+'さんと対戦中、あなたのターンです。\n '+
                'King,Queenのアクションをメニューから選んで場所を指定してくださいρ(-ω- )'))
        else:
            if getKingOrderStatus(sourceId) == 'ordered' and matcher.group(1) == 'KING':
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='( ﾟﾛﾟ)Kingはすでに行動済です'))
            elif getQueenOrderStatus(sourceId) == 'ordered' and matcher.group(1) == 'QUEEN':
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text='( ﾟﾛﾟ)Queenはすでに行動済です'))

def push_all_room_member(roomId, message):
    for i in range(0,redis.llen(roomId)):
        line_bot_api.push_message(
            redis.lindex(roomId,i),
            TextSendMessage(text=message))

def push_all_room_member_sticker(roomId, event):
    pack = event.message.package_id
    if pack == 1 or pack == 2 or pack ==3:
        for i in range(0,redis.llen(roomId)):
            line_bot_api.push_message(
                redis.lindex(roomId,i),
                StickerSendMessage(
                    package_id=event.message.package_id,
                    sticker_id=event.message.sticker_id))
    else:
        push_all_room_member(roomId,'＜スタンプ＞*対応できませんでした')



def generateAckMsg(fromUserName):
    pass

def generateRejectMsg(fromUserName):
    pass

def generateInviteMsg(fromUserName,fromUserId):
    #スペース抑制
    if fromUserName.find(' ') > 0:
        fromUserName.replace(' ','_')
    if fromUserName.find('　') > 0:
        fromUserName.replace('　','_')

    line_bot_api.push_message(fromUserId,TextSendMessage(text=fromUserName))


    buttons_template = ButtonsTemplate(
        title='挑戦者',
        text=fromUserName+'さんからの対戦申し込みです',
        thumbnail_image_url=getImage(fromUserId),
        actions=[
            MessageTemplateAction(label='OK！', text='ACK__'+fromUserId),
            MessageTemplateAction(label='あとで', text='REJECT__'+fromUserId)
    ])
    template_message = TemplateSendMessage(
        alt_text='対戦しよーぜ！', template=buttons_template)
    return template_message

def generateQuitConfirm():
    pass

def displayInitialMap():
    pass


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
