# -*- coding: utf-8 -*-

import os
import time
import logging

from websocket import create_connection

import slacker_blocks
from slackbot import slackclient

logger = logging.getLogger(__name__)


class BlocksSlackClient(slackclient.SlackClient):
    """
    Overrides to support blocks in calls.
    """

    def __init__(self, token, timeout=None, bot_icon=None, bot_emoji=None, connect=True):
        super(BlocksSlackClient, self).__init__(
            # Never connect since we'll do that here
            token, timeout=timeout, bot_icon=bot_icon, bot_emoji=bot_emoji, connect=False
        )
        # Replace the webapi with the blocks-supporting version
        if timeout is None:
            self.webapi = slacker_blocks.Slacker(self.token)
        else:
            self.webapi = slacker_blocks.Slacker(self.token, timeout=timeout)

        if connect:
            self.rtm_connect()

    def rtm_connect(self):
        reply = self.webapi.rtm.connect().body
        time.sleep(1)
        self.parse_slack_login_data(reply)

    def send_message(self, channel, message, attachments=None, blocks=None, as_user=True, thread_ts=None):
        self.webapi.chat.post_message(
                channel,
                message,
                username=self.login_data['self']['name'],
                icon_url=self.bot_icon,
                icon_emoji=self.bot_emoji,
                attachments=attachments,
                blocks=blocks,
                as_user=as_user,
                thread_ts=thread_ts)

    def parse_slack_login_data(self, login_data):
        self.login_data = login_data
        self.domain = self.login_data['team']['domain']
        self.username = self.login_data['self']['name']
        self.parse_user_data(self.webapi.users.list().body['members'])
        self.parse_channel_data(self.webapi.conversations.list().body['channels'])

        proxy, proxy_port, no_proxy = None, None, None
        if 'http_proxy' in os.environ:
            proxy, proxy_port = os.environ['http_proxy'].split(':')
        if 'no_proxy' in os.environ:
            no_proxy = os.environ['no_proxy']

        self.websocket = create_connection(self.login_data['url'], http_proxy_host=proxy,
                                           http_proxy_port=proxy_port, http_no_proxy=no_proxy)

        self.websocket.sock.setblocking(0)
