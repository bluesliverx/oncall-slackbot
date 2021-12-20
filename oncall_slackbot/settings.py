# -*- coding: utf-8 -*-

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

# Import all slackbot settings as well, this also handles loading env vars, etc
# DO NOT MOVE THIS - IT WILL BREAK THINGS
from slackbot.settings import *  # noqa

if PLUGINS == ['slackbot.plugins']:
    # Override default plugins
    PLUGINS = [
        'oncall_slackbot.plugins',
        'slackbot.plugins',
    ]
