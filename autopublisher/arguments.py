import argparse
import os
import pwd
from argparse import ArgumentTypeError
from collections.abc import Callable
from typing import Any

import configargparse
from aiomisc.log import LogFormat, LogLevel


def validate(
    type: Callable[[Any], Any], constrain: Callable[[Any], bool]
) -> Callable[[Any], Any]:
    def wrapper(value: Any) -> Any:
        value = type(value)
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
        os.path.join(os.path.expanduser("~"), "autopublisher.conf"),
        "/etc/autopublisher/autopublisher.conf",
    ],
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    ignore_unknown_config_file_keys=True,
)

parser.add_argument("-D", "--debug", action="store_true")

parser.add_argument(
    "-u", "--user", required=False, help="Change process UID", type=pwd.getpwnam
)

group = parser.add_argument_group("Logging options")
group.add_argument("--log-level", default=LogLevel.info, choices=LogLevel.choices())
group.add_argument("--log-format", choices=LogFormat.choices(), default=LogFormat.color)
