import logging
import os
from argparse import Namespace
from sys import argv

from aiomisc_log import basic_config
from setproctitle import setproctitle

from autopublisher.arguments import parser
from autopublisher.services.telegrambot import TelegramBot

log = logging.getLogger(__name__)


def run_master(name: str, args: Namespace) -> None:
    log.info("Master with PID %s started", os.getpid())
    setproctitle(f"[Master] {name}")
    service = TelegramBot()
    service.start()


def main() -> None:
    args = parser.parse_args()
    os.environ.clear()

    basic_config(
        level=args.log_level,
        log_format=args.log_format,
    )

    if args.user is not None:
        logging.info("Changing user to %r", args.user.pw_name)
        os.setgid(args.user.pw_gid)
        os.setuid(args.user.pw_uid)

    app_name = os.path.basename(argv[0])

    run_master(app_name, args)
