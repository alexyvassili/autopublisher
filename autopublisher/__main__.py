import logging
import os
from argparse import Namespace
from pathlib import Path
from sys import argv

from aiomisc_log import basic_config
from setproctitle import setproctitle

from autopublisher.arguments import parser
from autopublisher.config import config
from autopublisher.services.telegrambot import TelegramBot


log = logging.getLogger(__name__)


def set_config(args: Namespace) -> None:
    config.telegram_bot_owner_id = args.telegram_bot_owner_id
    config.mail_server = args.mail_server
    config.mail_login = args.mail_login
    config.mail_passwd = args.mail_passwd
    config.mail_from = args.mail_from
    config.alternate_mail = args.mail_alternate
    config.site_url = args.site_url
    config.site_username = args.site_username
    config.site_passwd = args.site_passwd
    config.server_mode = args.server_mode


def run_master(name: str, args: Namespace) -> None:
    log.info("Master with PID %s started", os.getpid())
    setproctitle(f"[Master] {name}")
    set_config(args)
    service = TelegramBot(
        token=args.telegram_bot_token,
        proxy_url=args.telegram_bot_proxy_url,
        proxy_port=args.telegram_bot_proxy_port,
        proxy_username=args.telegram_bot_proxy_username,
        proxy_passwd=args.telegram_bot_proxy_passwd,
    )
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

    app_name = Path(argv[0]).name

    run_master(app_name, args)
