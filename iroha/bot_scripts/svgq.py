"""
on: ^SVGQ\.(.*)
"""

from iroha import api

api.profile.username = "ChatGPT"
api.profile.icon_url = "https://4.bp.blogspot.com/-Anllqq6pDXw/VRUSesbvyAI/AAAAAAAAsrc/CIHz6vLsuTU/s400/computer_jinkou_chinou.png"

system = """
あなたは質問に対して、SVG形式の画像を生成します。
その説明部分を行った後、 <svg>...</svg> の形式で返してください。
単に指定された文字列を表示するのではなく、そのイメージ画像を生成してください.
""".strip()


def get_svg(query: str) -> str:
    text = api.internet.query.chat_assistant_openai(user=query, system=system)
    return api.publish.to_file_in_tags(text, "<svg ", "</svg>", "svg").replace(
        "```", ""
    )


if __name__ == "__main__":
    if len(api.argv) == 1:
        text = get_svg(api.argv[0])
    else:
        text = get_svg("ドラえもん")
    api.write(text)
