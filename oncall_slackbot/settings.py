# -*- coding: utf-8 -*-

import os
# pylint: disable=wildcard-import,unused-wildcard-import

DEBUG = False

ERRORS_TO = None

'''
Setup timeout for slacker API requests (e.g. uploading a file).
'''
TIMEOUT = 100

# API_TOKEN = '###token###'

'''
Setup a comma delimited list of aliases that the bot will respond to.

Example: if you set ALIASES='!,$' then a bot which would respond to:
'botname hello'
will now also respond to
'$ hello'
'''
ALIASES = ''

'''
If you use Slack Web API to send messages (with
send_webapi(text, as_user=False) or reply_webapi(text, as_user=False)),
you can customize the bot logo by providing Icon or Emoji. If you use Slack
RTM API to send messages (with send() or reply()), or if as_user is True
(default), the used icon comes from bot settings and Icon or Emoji has no
effect.
'''
# BOT_ICON = 'http://lorempixel.com/64/64/abstract/7/'
# BOT_EMOJI = ':godmode:'

# Specify a different reply when the bot is messaged with no matching cmd
DEFAULT_REPLY = None


'''
Pager duty configuration, these are optional but both must be specified in
order to enable pager duty integration.
'''
PAGERDUTY_TOKEN = None
PAGERDUTY_SCHEDULE_ID = None


'''
(Optional, only works if pager duty is configured) Configures the email domain used to determine user names from emails.
For example, emails of the form 'myuser@example.com' should configure this property with a value of 'example.com'
(exclude the @ prefix). This would result in 'myuser' being set as the user name.
'''
PAGERDUTY_USERNAME_EMAIL_DOMAIN = None


'''
Spacy configuration, this is optional
'''
SPACY_MODEL = None

PLUGINS = [
    'oncall_slackbot.plugins',
]

for key in os.environ:
    if key[:9] == 'SLACKBOT_':
        name = key[9:]
        globals()[name] = os.environ[key]

# pylint: disable=unused-wildcard-import
try:
    from slackbot_settings import *
except ImportError:
    try:
        from local_settings import *
    except ImportError:
        pass

# convert default_reply to DEFAULT_REPLY
try:
    DEFAULT_REPLY = default_reply
except NameError:
    pass
