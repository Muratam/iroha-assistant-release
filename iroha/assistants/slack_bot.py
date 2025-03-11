from slack import RTMClient
from iroha import api
from typing import Any
import asyncio


def run_matching_script(data: dict, script: api.script.Script) -> None:
    # 制約チェック
    for key in ["channel", "subtype", "bot_id"]:
        if (key in data) and (key in script.filters):
            if data[key] not in script.filters[key]:
                return
    # subtype設定がないものは、subtypeがあるBotには返答しない
    if "subtype" not in script.filters:
        if data.get("subtype", "") != "":
            return
    # 非同期に実行
    text = data.get("text", "")
    task = asyncio.create_task(script.run_if_match(text, api.script.RunMode.SLACK))
    # asyncio.gather(task)


@RTMClient.run_on(event="message")
def on_message(**payload: dict[str, Any]) -> None:
    try:
        # クエリが来るたびにパースすることで、再起動不要に
        data = payload.get("data", {})
        for script in api.script.iterate_all_iroha_bot_scripts():
            run_matching_script(data, script)
    except Exception as e:
        api.log.exception(str(e), exc_info=e)


def start() -> None:
    api.log.info("start")
    RTMClient(token=api.secret.slack_token).start()
