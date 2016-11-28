# -*- coding: utf-8 -*-

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

class Poker(object):

    ELEMENT_WIDTH = 260
    ELEMENT_HEIGHT = 263

    def __init__(self, redis, sourceId):
        self._redis = redis
        self._id = str(redis.incr(sourceId)).encode('utf-8')

    def generatePlanningPokerMessage(self):
        message = ImagemapSendMessage(
            base_url='https://scrummasterbot.herokuapp.com/images/planning_poker',
            alt_text='this is planning poker',
            base_size=BaseSize(height=790, width=1040))
        actions=[]
        location=0
        for i in range(0, 3):
            for j in range(0, 4):
                actions.append(MessageImagemapAction(
                    text = u'#' + self._id + u' ' + str(location).encode('utf-8'),
                    area=ImagemapArea(
                        x=j * self.ELEMENT_WIDTH,
                        y=i * self.ELEMENT_HEIGHT,
                        width=(j + 1) * self.ELEMENT_WIDTH,
                        height=(i + 1) * self.ELEMENT_HEIGHT
                    )
                ))
                ++location
        message.actions = actions
        return message


