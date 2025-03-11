"""
on: ^HTMLQ\.(.*)
"""

from iroha import api

api.profile.username = "ChatGPT"
api.profile.icon_url = "https://4.bp.blogspot.com/-Anllqq6pDXw/VRUSesbvyAI/AAAAAAAAsrc/CIHz6vLsuTU/s400/computer_jinkou_chinou.png"

start_tag = """<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>"""
end_tag = "</html>"
system = f"""
あなたは質問に対して、HTML形式で返答を生成します。
回答は、その説明部分を行った後、 {start_tag}...{end_tag} の形式で返してください。
""".strip()


def get_html(query: str) -> str:
    expanded = api.publish.expand_published_files(query)
    # 4oにモデルが下がってしまうので無効化
    # if len(expanded.expanded_file_pathes) > 0:
    #     predication = "\n\n".join(expanded.expanded_file_contents)
    text = api.internet.query.chat_assistant_openai(
        expanded.expanded_text, system=system
    )
    return api.publish.to_file_in_tags(text, start_tag, end_tag, "html").replace(
        "```", ""
    )


if __name__ == "__main__":
    if len(api.argv) == 1:
        query = api.argv[0]
    else:
        query = "15パズルのゲームを作ってください。"
    api.write(f"HTMLQ のリクエスト内容を生成します")
    text = get_html(query)
    api.write(text)
