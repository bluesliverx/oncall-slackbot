# -*- coding: utf-8 -*-
import logging
import re
from oncall_slackbot.integrations import nlp
from slackbot import bot, manager
from oncall_slackbot.slackclient import BlocksSlackClient
from oncall_slackbot.dispatcher import OnCallMessageDispatcher
from oncall_slackbot import settings

logger = logging.getLogger(__name__)


class OnCallBot(bot.Bot):
    """
    Override to instantiate custom versions of objects.
    """
    def __init__(self):
        # Do not call super init since we are going to override everything anyways
        self._client = BlocksSlackClient(
            settings.API_TOKEN,
            timeout=settings.TIMEOUT if hasattr(settings, 'TIMEOUT') else None,
            bot_icon=settings.BOT_ICON if hasattr(settings, 'BOT_ICON') else None,
            bot_emoji=settings.BOT_EMOJI if hasattr(settings, 'BOT_EMOJI') else None
        )
        self._plugins = manager.PluginsManager()
        # Load all plugins
        for plugin in settings.PLUGINS:
            self._plugins._load_plugins(plugin)
        self._dispatcher = OnCallMessageDispatcher(self._client, self._plugins, settings.ERRORS_TO)


def nlp_label_respond_to(match_label, flags=0):
    def wrapper(func):
        if nlp.is_backend_present():
            manager.PluginsManager.commands['nlp_label_respond_to'][re.compile(match_label, flags)] = func
            logger.info(f'registered nlp_label_respond_to plugin "{func.__name__}" to "{match_label}"')
        else:
            logger.warning(f'no NLP backend is configured to handle nlp_label_respond_to for "{func.__name__}"')
        return func

    return wrapper


def nlp_label_listen_to(match_label, flags=0):
    def wrapper(func):
        if nlp.is_backend_present():
            manager.PluginsManager.commands['nlp_label_listen_to'][re.compile(match_label, flags)] = func
            logger.info(f'registered nlp_label_listen_to plugin "{func.__name__}" to "{match_label}"')
        else:
            logger.warning(f'no NLP backend is configured to handle nlp_label_listen_to for "{func.__name__}"')
        return func

    return wrapper


if nlp.is_backend_present():
    if 'nlp_label_respond_to' not in manager.PluginsManager.commands:
        manager.PluginsManager.commands['nlp_label_respond_to'] = {}
    if 'nlp_label_listen_to' not in manager.PluginsManager.commands:
        manager.PluginsManager.commands['nlp_label_listen_to'] = {}
