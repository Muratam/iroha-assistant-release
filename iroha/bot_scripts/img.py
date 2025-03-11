"""
on: ^IMG\.(.*)
"""

from iroha import api

api.profile.username = "OpenAI Image Generation"
api.profile.icon_url = "https://4.bp.blogspot.com/-Anllqq6pDXw/VRUSesbvyAI/AAAAAAAAsrc/CIHz6vLsuTU/s400/computer_jinkou_chinou.png"

if __name__ == "__main__":
    if len(api.argv) == 1:
        text = api.internet.query.generate_image_openai(api.argv[0])
    else:
        text = api.internet.query.generate_image_openai("this is a test")
    api.write(text)
