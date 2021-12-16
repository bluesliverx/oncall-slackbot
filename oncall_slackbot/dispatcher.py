# -*- coding: utf-8 -*-

import logging
import traceback

from slackbot.slackclient import SlackClient
from slackbot import dispatcher
from oncall_slackbot import settings
from oncall_slackbot.integrations import nlp

logger = logging.getLogger(__name__)


class OnCallMessageDispatcher(dispatcher.MessageDispatcher):
    """
    Overrides to add support for NLP processing.
    """

    def dispatch_msg(self, msg):
        if len(msg) > 2:
            override_match_text = msg[2]
        else:
            override_match_text = None

        category = msg[0]
        msg = msg[1]
        if not self._dispatch_msg_handler_override(category, msg, override_match_text):
            # TODO Fix this for both nlp and non-nlp responds. For now I'm leaving it as the default behavior
            #   of only handling non-nlp responds for the default reply
            # Send the default reply if nlp doesn't respond with anything
            # and there is an nlp label and this is for an nlp label match
            # or if there is no nlp label and this is not for an nlp label match
            # NOTE: This isn't really ideal as respond_to could respond with something when nlp_respond_to did not
            #   but it is a stop-gap that should work most of the time since most won't be combining nlp with non-nlp
            #   plugins I would imagine
            # if (category == 'respond_to' and not msg.get('nlp_label')) or \
            #         (category == 'nlp_label_respond_to' and msg.get('nlp_label')):
            #     if not self._dispatch_msg_handler_override('default_reply', msg, override_match_text):
            #         self._default_reply(msg)
            if category == u'respond_to':
                if not self._dispatch_msg_handler('default_reply', msg):
                    self._default_reply(msg)

    def _dispatch_msg_handler_override(self, category, msg, override_match_text):
        responded = False
        match_text = override_match_text or msg.get('text', None)
        for func, args in self._plugins.get_plugins(category, match_text):
            if func:
                responded = True
                try:
                    func(OnCallMessage(self._client, msg), *args)
                except Exception:
                    logger.exception(
                        'failed to handle message %s with plugin "%s"',
                        msg['text'], func.__name__)
                    reply = f'[{func.__name__}] I had a problem handling "{msg["text"]}"\n'
                    tb = f'```\n{traceback.format_exc()}\n```'
                    if self._errors_to:
                        self._client.rtm_send_message(msg['channel'], reply)
                        self._client.rtm_send_message(self._errors_to, f'{reply}\n{tb}')
                    else:
                        self._client.rtm_send_message(msg['channel'], f'{reply}\n{tb}')
        return responded

    def _on_new_message(self, msg):
        # ignore edits
        subtype = msg.get('subtype', '')
        if subtype == 'message_changed':
            return

        botname = self._get_bot_name()
        try:
            msguser = self._client.users.get(msg['user'])
            username = msguser['name']
        except (KeyError, TypeError):
            if 'username' in msg:
                username = msg['username']
            else:
                return

        if username == botname or username == 'slackbot':
            return

        # Add nlp label if available (this results in a no-op if not available)
        nlp_label = nlp.generate_label(msg.get('text', '') or '')
        msg['nlp_label'] = nlp_label

        msg_respond_to = self.filter_text(msg)
        if msg_respond_to:
            self._pool.add_task(('respond_to', msg_respond_to))
            if nlp_label:
                self._pool.add_task(('nlp_label_respond_to', msg_respond_to, nlp_label))
        else:
            self._pool.add_task(('listen_to', msg))
            if nlp_label:
                self._pool.add_task(('nlp_label_listen_to', msg, nlp_label))

    def _default_reply(self, msg):
        default_reply = settings.DEFAULT_REPLY
        if default_reply is None:
            default_reply = [
                u'Bad command "{}", You can ask me one of the following '
                u'questions:\n'.format(
                    msg['text']),
            ]
            default_reply += [
                u'    • `{0}` {1}'.format(p.pattern, v.__doc__ or "")
                for p, v in
                self._plugins.commands['respond_to'].items()]
            # pylint: disable=redefined-variable-type
            default_reply = u'\n'.join(default_reply)

        m = OnCallMessage(self._client, msg)
        m.reply(default_reply)


class OnCallMessage(dispatcher.Message):
    """
    Overrides a message to add support for blocks.
    """

    @dispatcher.unicode_compact
    def reply_webapi(self, text, attachments=None, blocks=None, as_user=True, in_thread=None):
        """
            Send a reply to the sender using Web API

            (This function supports formatted message
            when using a bot integration)

            If the message was send in a thread, answer in a thread per default.
        """
        if in_thread is None:
            in_thread = 'thread_ts' in self.body

        if in_thread:
            self.send_webapi(text, attachments=attachments, blocks=blocks, as_user=as_user, thread_ts=self.thread_ts)
        else:
            text = self.gen_reply(text)
            self.send_webapi(text, attachments=attachments, blocks=blocks, as_user=as_user)

    @dispatcher.unicode_compact
    def send_webapi(self, text, attachments=None, blocks=None, as_user=True, thread_ts=None):
        """
            Send a reply using Web API

            (This function supports formatted message
            when using a bot integration)
        """
        self._client.send_message(
            self._body['channel'],
            text,
            attachments=attachments,
            blocks=blocks,
            as_user=as_user,
            thread_ts=thread_ts)

    @property
    def client(self) -> SlackClient:
        return self._client

    @property
    def nlp_label(self):
        return self._body.get('nlp_label')
