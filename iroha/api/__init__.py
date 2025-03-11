from . import script
import sys
import logging
from typing import Any


class Profile:
    def __init__(self) -> None:
        self.username = "BOT"
        self.icon_url = "https://picsum.photos/200.jpg"
        self.channel: str | None = None  # FIXME: 別の場所で管理したい


argv = sys.argv[1:]
profile = Profile()
log = logging.getLogger("[iroha]")


def write(may_text: Any) -> None:
    text = str(may_text)
    from . import internet

    run_mode = script.get_run_mode()
    if run_mode == script.RunMode.SLACK:
        internet.post.to_slack(
            text=text,
            username=profile.username,
            icon_url=profile.icon_url,
            channel=profile.channel,
        )
    else:
        print(text)


def write_as_debug(may_text: Any) -> None:
    text = str(may_text)
    from . import internet

    run_mode = script.get_run_mode()
    if run_mode == script.RunMode.SLACK:
        internet.post.to_slack(
            text=text,
            username=profile.username,
            icon_url=profile.icon_url,
            channel=secret.response_debug_slack_channel_id,
        )
    else:
        print(text)


if not log.handlers:
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    class WriteHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            write(f"[{record.levelname}] {self.format(record)}")

    log.addHandler(WriteHandler())
    run_mode = script.get_run_mode()
    if run_mode == script.RunMode.SLACK:
        loglevel = logging.WARNING
    else:
        loglevel = logging.INFO
    log.setLevel(loglevel)

from . import secret, openai, internet, publish
