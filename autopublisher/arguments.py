import argparse
import pwd
from argparse import ArgumentTypeError
from collections.abc import Callable
from pathlib import Path
from typing import Any

import configargparse
from aiomisc.log import LogFormat, LogLevel
from yarl import URL


def validate(
    type_: Callable[[Any], Any], constrain: Callable[[Any], bool],
) -> Callable[[Any], Any]:
    def wrapper(value: Any) -> Any:
        value = type_(value)
        if not constrain(value):
            raise ArgumentTypeError
        return value

    return wrapper


uint = validate(int, constrain=lambda x: x > 0)


parser = configargparse.ArgumentParser(
    allow_abbrev=False,
    auto_env_var_prefix="APP_",
    description="Script for automatic publish news "
                "and updates from email to drupal site",
    default_config_files=[
        (Path("~") / ".autopublisher.conf").expanduser(),
        "/etc/autopublisher/autopublisher.conf",
    ],
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    ignore_unknown_config_file_keys=True,
)

parser.add_argument("-D", "--debug", action="store_true")

parser.add_argument(
    "-u", "--user", required=False, help="Change process UID", type=pwd.getpwnam,
)

parser.add_argument(
    "--server-mode",
    action="store_true",
    help="Use headless selenium driver mode on server",
)

group = parser.add_argument_group("Mail options")
group.add_argument("--mail-server", type=str, required=True)
group.add_argument("--mail-login", type=str, required=True)
group.add_argument("--mail-passwd", type=str, required=True)
group.add_argument("--mail-from", type=str, required=True)
group.add_argument("--mail-alternate", type=str, required=True)

group = parser.add_argument_group("Site options")
group.add_argument("--site-url", type=URL, required=True)
group.add_argument("--site-username", type=str, required=True)
group.add_argument("--site-passwd", type=str, required=True)

group = parser.add_argument_group("Telegram bot options")
group.add_argument("--telegram-bot-token", type=str, required=True)
group.add_argument("--telegram-bot-owner-id", type=int, required=True)

group = parser.add_argument_group("Telegram bot proxy options")
group.add_argument("--telegram-bot-proxy-url", type=URL, default=None)
group.add_argument("--telegram-bot-proxy-port", type=uint, default=None)
group.add_argument("--telegram-bot-proxy-username", type=str, default=None)
group.add_argument("--telegram-bot-proxy-passwd", type=str, default=None)

group = parser.add_argument_group("Logging options")
group.add_argument(
    "--log-level", default=LogLevel.info, choices=LogLevel.choices(),
)
group.add_argument(
    "--log-format", choices=LogFormat.choices(), default=LogFormat.color,
)
