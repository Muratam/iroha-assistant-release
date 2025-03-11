from iroha import api
import random
import string
import os
import re
import requests
import json


def to_gyazo(imagedata: bytes) -> str:
    response = requests.request(
        "post",
        "https://upload.gyazo.com/api/upload",
        headers={"Authorization": "Bearer " + api.secret.gyazo_token},
        files={"imagedata": imagedata},
    )
    return str(json.loads(response.text)["url"])


def to_file(data: str | bytes, ext: str) -> str:
    if ext.startswith("."):
        ext = ext[1:]
    random_path = (
        "".join(random.choices(string.ascii_letters + string.digits, k=8)) + "." + ext
    )
    local_path = os.path.join(api.secret.local_path_prefix, random_path)
    publish_path = os.path.join(api.secret.publish_path_prefix, random_path)
    if isinstance(data, bytes):
        with open(local_path, "wb") as f:
            f.write(data)
    else:
        with open(local_path, "w") as f:
            f.write(data)
    return publish_path


def to_file_in_tags(text: str, start_tag: str, end_tag: str, ext: str) -> str:
    start = text.find(start_tag)
    end = text.rfind(end_tag)
    if start == -1 or end == -1:
        return text
    content = start_tag + text[start + len(start_tag) : end] + end_tag
    return text[:start] + to_file(content, ext) + text[end + len(end_tag) :]


def read_published_file(published_path: str) -> str:
    local_path = published_path.replace(
        api.secret.publish_path_prefix, api.secret.local_path_prefix
    )
    # Normalize paths to ensure consistent comparison
    local_path = os.path.normpath(local_path)
    norm_local_path_prefix = os.path.normpath(api.secret.local_path_prefix)
    # Check if local_path is a subdirectory of local_path_prefix
    if (
        not os.path.commonpath([local_path, norm_local_path_prefix])
        == norm_local_path_prefix
    ):
        api.log.warning(f"{local_path} is not subdirectory")
        return ""
    if not os.path.isfile(local_path):
        api.log.warning(f"{local_path} is not filey")
        return ""
    with open(local_path, "r") as f:
        return f.read()


class ExpandedResult:
    def __init__(
        self,
        base_text: str,
        expanded_text: str,
        expanded_file_contents: list[str],
        expanded_file_pathes: list[str],
    ):
        self.base_text = base_text
        self.expanded_text = expanded_text
        self.expanded_file_contents = expanded_file_contents
        self.expanded_file_pathes = expanded_file_pathes


def expand_published_files(base_text: str, max_count: int = 3) -> ExpandedResult:
    count = 0
    start = 0
    expanded_text = f"{base_text}"
    expanded_file_contents = []
    expanded_file_pathes = []
    while count < max_count:
        start = expanded_text.find(api.secret.publish_path_prefix, start)
        if start == -1:
            break
        match = re.search(r'[ \t\n!"\$\'\(\)\|\[\]\{\};\*<>}]', expanded_text[start:])
        if match:
            end = start + match.start()
        else:
            end = len(expanded_text)
        expanded_file_path = expanded_text[start:end]
        expanded_file_content = read_published_file(expanded_file_path)
        expanded_text = (
            expanded_text[:start] + expanded_file_content + expanded_text[end:]
        )
        count += 1
        start += len(expanded_file_content)
        expanded_file_contents.append(expanded_file_content)
        expanded_file_pathes.append(expanded_file_path)
    if count >= max_count:
        api.log.warning("too many files expanding")
    return ExpandedResult(
        base_text, expanded_text, expanded_file_contents, expanded_file_pathes
    )
