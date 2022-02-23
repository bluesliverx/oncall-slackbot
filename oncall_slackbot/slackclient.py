# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import
import os
import json
import logging
import time

from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
from slack_sdk.rtm_v2 import RTMClient

logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class SlackClient:
    # pylint: disable=too-many-arguments
    def __init__(self, token, timeout=None, bot_icon=None, bot_emoji=None, connect=True,
                 rtm_start_args=None, rtm_handlers=None):
        self.token = token
        self.bot_icon = bot_icon
        self.bot_emoji = bot_emoji
        self.username = None
        self.domain = None
        self.login_data = None
        self.users = {}
        self.channels = {}
        self.connected = False
        self.rtm_start_args = rtm_start_args

        if timeout is None:
            self.rtm = RTMClient(token=self.token)
        else:
            self.rtm = RTMClient(token=self.token, timeout=timeout, on_message_listeners=rtm_handlers)

        rate_limit_handler = RateLimitErrorRetryHandler(max_retry_count=100)
        # Enable rate limited error retries
        self.rtm.web_client.retry_handlers.append(rate_limit_handler)

        if connect:
            self.rtm_connect()

    def start(self):
        self.rtm.start()

    def rtm_connect(self):
        reply = self.rtm.web_client.rtm_connect()
        self.parse_slack_login_data(reply)
        self.connected = True

    def reconnect(self):
        while True:
            try:
                self.rtm_connect()
                logger.warning('reconnected to slack rtm websocket')
                return
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception('failed to reconnect: %s', exc)
                time.sleep(5)

    def parse_slack_login_data(self, login_data):
        self.login_data = login_data
        self.domain = self.login_data['team']['domain']
        self.username = self.login_data['self']['name']

        logger.debug('Getting users')
        for page in self.rtm.web_client.users_list(limit=200):
            self.parse_user_data(page['members'])
        logger.debug('Getting channels')
        for page in self.rtm.web_client.conversations_list(
                exclude_archived=True,
                types="public_channel,private_channel",
                limit=1000
        ):
            self.parse_channel_data(page['channels'])

    def parse_channel_data(self, channel_data):
        logger.debug('Adding %d users', len(channel_data))
        self.channels.update({c['id']: c for c in channel_data})

    def parse_user_data(self, user_data):
        logger.debug('Adding %d users', len(user_data))
        self.users.update({u['id']: u for u in user_data})

    def send_to_rtm(self, data):
        """Send (data) directly to the RTMClient."""
        data = json.dumps(data)
        self.rtm.send(data)

    def rtm_send_message(self, channel, message, attachments=None, thread_ts=None):
        message_json = {
            'type': 'message',
            'channel': channel,
            'text': message,
            'attachments': attachments,
            'thread_ts': thread_ts,
            }
        self.send_to_rtm(message_json)

    def upload_file(self, channel, fname, fpath, comment):
        fname = fname or os.path.basename(fpath)
        self.rtm.web_client.files_upload(
            file=fpath,
            channels=channel,
            filename=fname,
            initial_comment=comment)

    def upload_content(self, channel, fname, content, comment):
        self.rtm.web_client.files_upload(
            channels=channel,
            content=content,
            filename=fname,
            initial_comment=comment)

    # pylint: disable=too-many-arguments
    def send_message(self, channel, message, attachments=None, blocks=None, as_user=True, thread_ts=None):
        self.rtm.web_client.chat_postMessage(
            channel=channel,
            text=message,
            username=self.login_data['self']['name'],
            icon_url=self.bot_icon,
            icon_emoji=self.bot_emoji,
            attachments=attachments,
            blocks=blocks,
            as_user=as_user,
            thread_ts=thread_ts)

    def get_channel(self, channel_id):
        return Channel(self, self.channels[channel_id])

    def open_dm_channel(self, user_id):
        return self.rtm.web_client.conversations_open(users=[user_id])["channel"]["id"]

    def find_channel_by_name(self, channel_name):
        for channel_id, channel in self.channels.items():
            try:
                name = channel['name']
            except KeyError:
                name = self.users[channel['user']]['name']
            if name == channel_name:
                return channel_id
        return None

    def get_user(self, user_id):
        return self.users.get(user_id)

    def find_user_by_name(self, username):
        for userid, user in self.users.items():
            if user['name'] == username:
                return userid
        return None

    def react_to_message(self, emojiname, channel, timestamp):
        self.rtm.web_client.reactions_add(
            name=emojiname,
            channel=channel,
            timestamp=timestamp)


class SlackConnectionError(Exception):
    pass


class Channel:
    def __init__(self, slackclient, body):
        self._body = body
        self._client = slackclient

    def __eq__(self, compare_str):
        name = self._body['name']
        cid = self._body['id']
        return compare_str in [name, f"#{name}", cid]

    def upload_file(self, fname, fpath, initial_comment=''):
        self._client.upload_file(self._body['id'], fname, fpath, initial_comment)

    def upload_content(self, fname, content, initial_comment=''):
        self._client.upload_content(self._body['id'], fname, content, initial_comment)
