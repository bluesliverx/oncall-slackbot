#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import logging.config
from oncall_slackbot import settings
from oncall_slackbot.bot import Bot


def main():
    kws = {
        "format": "[%(asctime)s] %(message)s",
        "datefmt": "%m/%d/%Y %H:%M:%S",
        "level": logging.DEBUG if settings.DEBUG else logging.INFO,
        "stream": sys.stdout,
    }
    logging.basicConfig(**kws)
    logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
        logging.WARNING
    )
    bot = Bot()
    bot.run()


if __name__ == "__main__":
    main()
