"""
on: ^Q\.(.*)
on: ^CFG\.(.*)Q\.(.*)
"""

from iroha import api

api.profile.username = "ChatGPT"
api.profile.icon_url = "https://4.bp.blogspot.com/-Anllqq6pDXw/VRUSesbvyAI/AAAAAAAAsrc/CIHz6vLsuTU/s400/computer_jinkou_chinou.png"

if __name__ == "__main__":
    if len(api.argv) == 0:
        text = api.internet.query.chat_assistant_openai("Say this is a test")
    elif len(api.argv) == 1:
        text = api.internet.query.chat_assistant_openai(api.argv[0])
    else:
        text = api.internet.query.chat_assistant_openai(api.argv[0], system=api.argv[1])
    api.write(text)
