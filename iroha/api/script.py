from iroha import api
import os
import ast
import asyncio
from enum import Enum
from typing import Self, Generator


class RunMode(Enum):
    DEFAULT = "DEFAULT"
    SLACK = "SLACK"


_iroha_script_run_mode_env_var_name = "IROHA_SCRIPT_RUN_MODE"


def get_run_mode() -> RunMode:
    value = os.environ.get(_iroha_script_run_mode_env_var_name, "")
    for cand in RunMode.__members__.values():
        if value == cand.value:
            return RunMode(value)
    return RunMode.DEFAULT


class Script:
    class Language(Enum):
        PYTHON = 0

    class Matcher:
        def __init__(self, pattern: str):
            self.pattern = pattern

        def _parse(self, text: str) -> list[str] | None:
            import re

            if text == "":
                return None
            found = re.search(self.pattern, text, re.MULTILINE | re.DOTALL)
            if not found:
                return None
            return list(found.groups())

    def __init__(
        self, language: Language, path: str, filters: dict, matchers: list[Matcher]
    ):
        self.language = language
        self.path = path
        self.filters = filters
        self.matchers = matchers

    @classmethod
    def from_file_path(cls, file_path: str) -> Self | None:
        if not os.path.isfile(file_path):
            return None
        if file_path.endswith(".py"):
            language = Script.Language.PYTHON
            with open(file_path, "r") as file:
                docstring = ast.get_docstring(
                    ast.parse(file.read(), filename=file_path)
                )
            if not docstring:
                return None
        else:
            return None
        filters: dict = {}
        matchers: list[Script.Matcher] = []
        for line in docstring.splitlines():
            if ":" not in line:
                continue
            cands = line.strip().split(":")
            key = cands[0].strip()
            value = ":".join(cands[1:]).strip()
            if key == "on":
                matchers.append(cls.Matcher(value))
            else:
                filters.setdefault(key, []).append(value)
        return cls(language, file_path, filters, matchers)

    async def run(self, argv: list[str], run_mode: RunMode) -> None:
        assert self.language == Script.Language.PYTHON
        commands = ["python", self.path] + argv
        env = {**os.environ, _iroha_script_run_mode_env_var_name: run_mode.value}
        api.log.info(commands)
        await asyncio.create_subprocess_exec(*commands, env=env)

    async def run_if_match(self, text: str, run_mode: RunMode) -> None:
        for matcher in self.matchers:
            argv = matcher._parse(text)
            if not (argv is None):
                await self.run(argv, run_mode)


def iterate_all_iroha_bot_scripts() -> Generator[Script, None, None]:
    script_dir = os.path.join(os.getcwd(), "iroha/bot_scripts/")
    for file_name in os.listdir(script_dir):
        script = Script.from_file_path(os.path.join(script_dir, file_name))
        if script:
            yield script
