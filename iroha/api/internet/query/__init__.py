from iroha import api
import requests
from typing import Any, Dict
from bs4 import BeautifulSoup

chat_openai = api.openai.chat
generate_image_openai = api.openai.generate_image


def chat_perplexity_raw(user: str, model: str) -> Any:
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise.",
            },
            {"role": "user", "content": user},
        ],
        "model": model,
    }
    headers = {
        "Authorization": f"Bearer {api.secret.perplexity_token}",
        "Content-Type": "application/json",
    }
    return requests.post(
        "https://api.perplexity.ai/chat/completions", headers=headers, json=payload
    ).json()


def chat_perplexity(user: str, model: str = "sonar") -> str:
    response = chat_perplexity_raw(user, model)
    content = response["choices"][0]["message"]["content"]
    result = f"{content}\n\n"
    for i, citation in enumerate(response["citations"]):
        if f"[{i+1}]" in content:
            result += f"\n[{i + 1}] {citation}"
    return result


def chat_assistant_openai(
    user: str,
    system: str = "You are a helpful assistant.",
    model: str = "gpt-4.5-preview",
) -> str:
    def query_internet(query: str) -> str:
        """
        この関数では最新の情報やニュースを基にしてqueryに対する回答を生成します。
        あなたが知らない情報がある場合はこの関数を使うことで外部の知識を得ることができます。

        Args:
          query: 質問の文字列"
        """
        api.write_as_debug(f"「 {query} 」でインターネットを検索しています")
        result = chat_perplexity(query)
        return result

    def read_webpage(url: str) -> str:
        """
        この関数を使うとURLにあるWebページの内容(テキストのみ)を取得できます。

        Args:
          url: WebページのURL
        """
        api.write_as_debug(f"{url} のWebページを読んでいます")
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            return soup.get_text()
        else:
            return f"Failed to retrieve content. Status code: {response.status_code}"

    with api.openai.TemporaryThread() as thread:
        assistant = api.openai.Assistant(api.secret.openai_temporary_assistant_id)
        thread.write_user_message(user)
        snapshot = api.openai.Runner(
            api.openai.RunnerHandler(
                [],
                [
                    api.openai.CodeInterpreterTool(),
                    api.openai.FunctionTool(query_internet, read_webpage),
                ],
            )
        ).run_until_done(thread, assistant, model=model, instructions=system)
        return snapshot
