# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import errno
import os
import re
import time

import redis

from flask_sqlalchemy import SQLAlchemy

from flask import Flask, request, abort, logging, send_from_directory

from linebot import (
    LineBotApi, WebhookHandler,
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, URITemplateAction, PostbackTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent,
    ImagemapSendMessage, MessageImagemapAction, MessageImagemapAction, BaseSize, ImagemapArea
)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
cache = redis.from_url(app.config['REDIS_URL'])

from app import models

line_bot_api = LineBotApi(app.config['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['CHANNEL_SECRET'])

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# function for create tmp dir for download content
def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise

@app.route("/callback", methods=['POST'])
def callback():

    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@app.route('/planning_poker/images/<size>', methods=['GET'])
def images(size):
    app.logger.info(size)
    return send_from_directory("static/planning_poker/", "pp-" + size +".png")

@app.route('/vote/<pokerId>/<teamId>/<pointId>', methods=['GET'])
def vote(pokerId, teamId, pointId):
    app.logger.info('Poker ID : ' + pokerId)
    app.logger.info('Team ID : ' + teamId)
    app.logger.info('Point ID : ' + pointId)
    return 'OK'


def getSourceId(source):
    sourceType = source.type
    if sourceType == 'user':
        app.logger.info("user id : " + source.user_id)
        return source.user_id
    elif sourceType == 'group':
        app.logger.info("group id : " + source.group_id)
        return source.group_id
    elif sourceType == 'room':
        app.logger.info("room id : " + source.room_id)
        return source.room_id
    else:
        abort(400)

EXCLUSIVE_CONTROL_KEY = 'exclusive'
EXCLUSIVE_CONTROL_KEY2 = 'exclusive2'
VOTE_PATTERN = r"^#(\d+) (\d+)"

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text
    sourceId = getSourceId(event.source)
    matchOB = re.match(VOTE_PATTERN, text)

    if text == 'プラポ':
        if cache.sismember(EXCLUSIVE_CONTROL_KEY, sourceId):
            pass
        else:
            cache.sadd(EXCLUSIVE_CONTROL_KEY, sourceId)
            pokerId = str(cache.incr(sourceId)).encode('utf-8')
            line_bot_api.reply_message(
                event.reply_token,
                generatePlanningPokerMessage(pokerId, sourceId))
    elif matchOB is not None:
        count = matchOB.group(1)
        location = matchOB.group(2)
        if cache.sismember(EXCLUSIVE_CONTROL_KEY2, sourceId):
            cache.hincrby(text, location)
        else:
            cache.sadd(EXCLUSIVE_CONTROL_KEY2, sourceId)
            cache.hincrby(text, location)
            time.sleep(10)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('10秒経ったよー')
            )

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    pass

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    pass

@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    pass

@handler.add(FollowEvent)
def handle_follow(event):
    pass

@handler.add(UnfollowEvent)
def handle_unfollow():
    pass

@handler.add(JoinEvent)
def handle_join(event):
    pass

@handler.add(LeaveEvent)
def handle_leave():
    pass

@handler.add(PostbackEvent)
def handle_postback(event):
    pass

@handler.add(BeaconEvent)
def handle_beacon(event):
    pass

def generatePlanningPokerMessage(pokerId, teamId):
    server_url = 'https://scrummasterbot.herokuapp.com/vote/'
    message = ImagemapSendMessage(
        base_url='https://scrummasterbot.herokuapp.com/planning_poker/images',
        alt_text='this is planning poker',# create tmp dir for download content
        base_size=BaseSize(height=790, width=1040),
        actions=[
            MessageImagemapAction(
                text = u'#' + pokerId + u' 0',
                area=ImagemapArea(
                    x=0, y=0, width=260, height=260
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 1',
                area=ImagemapArea(
                    x=260, y=0, width=515, height=260
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 2',
                area=ImagemapArea(
                    x=520, y=0, width=770, height=260
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 3',
                area=ImagemapArea(
                    x=720, y=0, width=1040, height=260
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 4',
                area=ImagemapArea(
                    x=0, y=260, width=260, height=520
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 5',
                area=ImagemapArea(
                    x=260, y=260, width=515, height=520
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 6',
                area=ImagemapArea(
                    x=520, y=260, width=770, height=520
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 7',
                area=ImagemapArea(
                    x=720, y=260, width=1040, height=520
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 8',
                area=ImagemapArea(
                    x=0, y=520, width=260, height=790
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 9',
                area=ImagemapArea(
                    x=260, y=520, width=515, height=790
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 10',
                area=ImagemapArea(
                    x=520, y=520, width=770, height=790
                )
            ),
            MessageImagemapAction(
                text = u'#' + pokerId + u' 11',
                area=ImagemapArea(
                    x=720, y=520, width=1040, height=790
                )
            )
        ]
    )
    return message

# create tmp dir for download content
make_static_tmp_dir()
