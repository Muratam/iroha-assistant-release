"""
on: ^美少女生成(.*)
"""

from iroha import api

api.profile.username = "OpenAI Image Generation"
api.profile.icon_url = "https://4.bp.blogspot.com/-Anllqq6pDXw/VRUSesbvyAI/AAAAAAAAsrc/CIHz6vLsuTU/s400/computer_jinkou_chinou.png"


def generate_girl(query: str) -> str:
    return api.internet.query.generate_image_openai(query + " アニメ スタイル 女の子")


if __name__ == "__main__":
    if len(api.argv) == 1:
        text = generate_girl(api.argv[0])
    else:
        text = generate_girl("this is a test")
    api.write(text)
