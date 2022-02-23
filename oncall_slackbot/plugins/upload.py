# -*- coding: utf-8 -*-

import os
from oncall_slackbot.bot import respond_to
from oncall_slackbot.utils import download_file, create_tmp_file


@respond_to(r'upload \<?(.*)\>?')
def upload(message, thing):
    # message.channel.upload_file(slack_filename, local_filename, initial_comment='')
    if thing == 'favicon':
        url = 'https://slack.com/favicon.ico'
        message.reply(f'uploading {url}')
        with create_tmp_file() as tmpf:
            download_file(url, tmpf)
            message.channel.upload_file(url, tmpf, f'downloaded from {url}')
    elif thing == 'slack.png':
        message.reply('uploading slack.png')
        cwd = os.path.abspath(os.path.dirname(__file__))
        fname = os.path.join(cwd, '../../tests/functional/slack.png')
        message.channel.upload_file(thing, fname)


@respond_to('send_string_content')
def upload_content(message):
    # message.channel.upload_content(slack_filename, content, initial_comment='')
    content = "你好! here's some data\nthat will appear\nas a plain text snippet"
    message.channel.upload_content('content.txt', content)
