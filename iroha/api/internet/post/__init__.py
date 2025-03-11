from iroha import api
import requests
from markdown_to_mrkdwn import SlackMarkdownConverter
from typing import Dict, Any


def to_slack(**data: Any) -> None:
    if not data.get("channel"):
        data["channel"] = api.secret.response_slack_channel_id
    data["text"] = SlackMarkdownConverter().convert(data["text"])
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {api.secret.slack_token}"},
        data=data,
    )
