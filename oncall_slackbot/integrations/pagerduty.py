
import logging
from datetime import datetime
from pytz import timezone, UTC
from typing import Optional
from pygerduty.v2 import PagerDuty, Oncall, User
from oncall_slackbot import settings
import humanize


LOGGER = logging.getLogger(__name__)


def is_configured() -> bool:
    return settings.PAGERDUTY_TOKEN and get_schedule_id()


def _get_client() -> Optional[PagerDuty]:
    if not is_configured():
        return None
    return PagerDuty(settings.PAGERDUTY_TOKEN)


def get_user_name(user: User) -> Optional[str]:
    if not settings.PAGERDUTY_USERNAME_EMAIL_DOMAIN:
        return None
    email_suffix = f'@{settings.PAGERDUTY_USERNAME_EMAIL_DOMAIN}'
    if not user.email.endswith(email_suffix):
        return None
    return user.email.replace(email_suffix, '')


def get_schedule_id():
    return settings.PAGERDUTY_SCHEDULE_ID


def get_humanized_datetime(datetime_string: str, dest_time_zone_str: Optional[str] = None) -> str:
    parsed = datetime.strptime(datetime_string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
    if dest_time_zone_str:
        dest_time_zone = timezone(dest_time_zone_str)
        parsed = parsed.astimezone(dest_time_zone)
    else:
        dest_time_zone = UTC
    result = humanize.naturaldate(parsed)
    if result != 'today':
        return result
    return humanize.naturaltime(datetime.now(dest_time_zone) - parsed)


def get_current_oncall() -> Optional[Oncall]:
    client = _get_client()
    if not client:
        LOGGER.debug('Pager duty settings are not configured, cannot retrieve current on call')
        return None

    oncalls = client.oncalls.list(include=['users'], schedule_ids=[get_schedule_id()])
    current_oncall = None
    for oncall in oncalls:
        current_oncall = oncall
        break
    if not current_oncall:
        return None
    return current_oncall
