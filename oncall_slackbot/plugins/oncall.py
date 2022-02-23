# -*- coding: utf-8 -*-

import logging
import re
from typing import Optional
from pygerduty.v2 import ContactMethod  # pylint: disable=import-error
from oncall_slackbot.bot import listen_to, Message
from oncall_slackbot.integrations import pagerduty

LOGGER = logging.getLogger(__name__)
CONTACT_METHOD_EMOTICON_BY_TYPE = {
    'email_contact_method': ':email:',
    'phone_contact_method': ':slack_call:',
    # Do not show anything for push or SMS notifications, since they duplicate the phone contact
    'sms_contact_method': None,
    'push_notification_contact_method': None,
}


def _get_contact_method_message(contact_method: ContactMethod, add_label: bool) -> Optional[str]:
    emoticon = CONTACT_METHOD_EMOTICON_BY_TYPE.get(contact_method.type)
    if not emoticon or (hasattr(contact_method, 'enabled') and not contact_method.enabled):
        return None
    label = ''
    if add_label:
        label = f' ({contact_method.label})'
    return f'{emoticon} {contact_method.address}{label}'


@listen_to(r'who is (?:currently )?on(?:-| |)call', re.IGNORECASE)
def who_is_on_call(message: Message):
    if not pagerduty.is_configured():
        LOGGER.debug('Pager duty settings are not configured, cannot retrieve current on call')
        return

    current_oncall = pagerduty.get_current_oncall()
    if not current_oncall:
        message.reply(f'No current on-call information found for schedule {pagerduty.get_schedule_id()}')
        return

    # Build up contact methods string
    contact_method_messages = []
    user_name = pagerduty.get_user_name(current_oncall.user)
    if user_name:
        contact_method_messages.append(f':slack: @{user_name}')
    contact_methods = current_oncall.user.contact_methods.list(time_zone='MDT')
    for contact_method in contact_methods:
        # Only add label if there is no user name
        contact_method_message = _get_contact_method_message(contact_method, not user_name)
        if contact_method_message:
            contact_method_messages.append(contact_method_message)

    # Get formatted end time
    end_time = pagerduty.get_humanized_datetime(current_oncall.end, current_oncall.user.time_zone)

    message.reply_webapi(f'{current_oncall.user.name} is currently on call', in_thread=True, blocks=[
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text":
                    f'*<{current_oncall.user.html_url}|{current_oncall.user.name}>* is on call '
                    f'<{current_oncall.schedule.html_url}|until {end_time}>'
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": '\n'.join(contact_method_messages)
            }
        },
    ])
