from iroha import api
from pprint import pprint
from typing import Self, Literal, Callable, get_args, get_origin
from pydantic import create_model, BaseModel, ValidationError
from typing import Any, Dict
import requests
import openai
import json
from openai.types.beta import AssistantStreamEvent
from openai.types.beta.threads import Run, Text, TextDelta
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from openai.types.chat import ChatCompletionPredictionContentParam


def create_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=api.secret.openai_token)


# https://platform.openai.com/assistants/
class Assistant:
    def __init__(self, assistant_id: str):
        self.id = assistant_id

    @classmethod
    def get_all(cls) -> list[Self]:
        return [cls(a.id) for a in create_client().beta.assistants.list().data]

    @classmethod
    def create_new(cls) -> Self:
        id = create_client().beta.assistants.create(model="gpt-4o").id
        return cls(id)

    def update(self, **data: Any) -> None:
        # tool_resources=..., # <- interpreter で コードを実行するときに利用
        create_client().beta.assistants.update(assistant_id=self.id, **data)

    def delete(self) -> None:
        create_client().beta.assistants.delete(assistant_id=self.id)

    def __str__(self) -> str:
        retrieved = create_client().beta.assistants.retrieve(assistant_id=self.id)
        return str(retrieved)


class Message:
    def __init__(self, message_id: str, thread_id: str):
        self.id = message_id
        self.thread_id = thread_id

    def __str__(self) -> str:
        retrieved = create_client().beta.threads.messages.retrieve(
            message_id=self.id, thread_id=self.thread_id
        )
        return str(retrieved)


class Thread:
    def __init__(self, thread_id: str):
        self.id = thread_id

    @classmethod
    def create_new(cls) -> Self:
        # NOTE あらかじめメッセージを作成して作ることもできる
        id = create_client().beta.threads.create().id
        return cls(id)

    def update(self, **data: Any) -> None:
        # NOTE metadata / tool_resources は後から変更できる.
        create_client().beta.threads.update(self.id, **data)

    def delete(self) -> None:
        create_client().beta.threads.delete(self.id)

    def write_user_message(self, content: str) -> Message:
        return self._write_message(content, "user")

    def write_assistant_message(self, content: str) -> Message:
        return self._write_message(content, "assistant")

    def _write_message(
        self, content: str, role: Literal["user", "assistant"]
    ) -> Message:
        message = create_client().beta.threads.messages.create(
            thread_id=self.id, role=role, content=content
        )
        return Message(message.id, self.id)

    def __str__(self) -> str:
        retrieved = create_client().beta.threads.retrieve(thread_id=self.id)
        return str(retrieved)


class TemporaryThread(Thread):
    def __init__(self) -> None:
        super().__init__(thread_id=Thread.create_new().id)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.delete()


class TextStreamEventHandler(openai.AssistantEventHandler):
    def __init__(self, verbose: bool = True):
        super().__init__()
        self.verbose = verbose

    def on_text_created(self, text: Text) -> None:
        if not self.verbose:
            return
        print(f"[assistant] ", end="", flush=True)

    def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        print(delta.value, end="", flush=True)

    def on_text_done(self, text: Text) -> None:
        if not self.verbose:
            return
        print("")

    def on_tool_call_created(self, tool_call: ToolCall) -> None:
        if not self.verbose:
            return
        if tool_call.type == "code_interpreter":
            print(f"[assistant: {tool_call.type}]", flush=True)

    def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall) -> None:
        if not self.verbose:
            return
        if delta.type == "code_interpreter":
            if code_interpreter := delta.code_interpreter:
                print(code_interpreter.input, end="", flush=True)
                if outputs := code_interpreter.outputs:
                    for output in outputs:
                        if output.type == "logs":
                            print(f"\n{output.logs}", end="", flush=True)

    def on_tool_call_done(self, tool_call: ToolCall) -> None:
        if not self.verbose:
            return
        if tool_call.type == "code_interpreter":
            print("")


class ToolInterface:
    def __init__(self) -> None:
        self.schemas: list = []

    def on_requires_action(self, data: Run) -> list:
        return []


class CodeInterpreterTool(ToolInterface):
    def __init__(self) -> None:
        self.schemas = [{"type": "code_interpreter"}]


def _parse_function_to_json_schema(func: Callable) -> Any:
    import docstring_parser

    parsed = docstring_parser.parse(func.__doc__ or "")
    properties: Dict[str, Any] = {}
    for name, param_type in func.__annotations__.items():
        type_name = ""
        enum_list = None
        if param_type is str:
            type_name = "string"
        elif get_origin(param_type) is Literal:
            type_name = "string"
            enum_list = get_args(param_type)
        elif param_type is int:
            type_name = "integer"
        elif param_type is float:
            type_name = "number"
        else:
            raise TypeError(f"Not Supported Type {param_type}")
        properties[name] = {
            "type": type_name,
        }
        if enum_list:
            properties[name]["enum"] = enum_list
    for param in parsed.params:
        if param.arg_name not in properties.keys():
            properties[param.arg_name] = {"type": "string"}
        if param.description:
            properties[param.arg_name]["description"] = param.description
    return {
        "type": "function",
        "function": {
            "strict": True,
            "name": func.__name__,
            "description": parsed.description,
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": list(properties.keys()),
                "properties": properties,
            },
        },
    }


def _create_pydantic_model_from_function(func: Callable) -> type[BaseModel]:
    annotations = func.__annotations__
    fields: Any = {k: (v, ...) for k, v in annotations.items()}
    del fields["return"]
    return create_model(f"{func.__name__ }Params", **fields)


class FunctionTool(ToolInterface):
    def __init__(self, *functions: Callable):
        # NOTE: functions の数は最大64くらい
        self.functions = {f.__name__: f for f in functions}
        self.schemas = [_parse_function_to_json_schema(f) for f in functions]
        self.Models = {
            f.__name__: _create_pydantic_model_from_function(f) for f in functions
        }

    def on_requires_action(self, data: Run) -> list:
        tool_outputs = []
        if action := data.required_action:
            for tool in action.submit_tool_outputs.tool_calls:
                if tool.function.name in self.Models:
                    arguments = json.loads(tool.function.arguments)
                    Model = self.Models[tool.function.name]
                    func = self.functions[tool.function.name]
                    try:
                        params = Model(**arguments)
                    except ValidationError as e:
                        # 型変換を試みる
                        converted_arguments: Any = arguments
                        for error in e.errors():
                            field = error["loc"][0]  # エラーのフィールド名を取得
                            field_type = Model.__annotations__[str(field)]
                            value = arguments[field]
                            try:
                                converted_arguments[field] = field_type(value)
                            except (ValueError, TypeError):
                                converted_arguments[field] = field_type()
                        params = Model(**converted_arguments)
                    output = func(**params.model_dump())

                    params = Model(**arguments)
                    output = func(**params.model_dump())
                    tool_outputs.append(
                        {"tool_call_id": tool.id, "output": str(output)}
                    )
        return tool_outputs


class RunnerHandler(openai.AssistantEventHandler):
    def __init__(
        self,
        event_handlers: list[openai.AssistantEventHandler],
        tools: list[ToolInterface],
    ):
        super().__init__()
        self.event_handlers = event_handlers
        self.tools = tools
        self.client: openai.Client | None = None
        self.assistant_snapshot: str = ""

    def on_before_run(self, client: openai.Client) -> None:
        self.client = client
        self.assistant_snapshot = ""

    def on_end_run(self) -> None:
        self.client = None

    def on_text_created(self, text: Text) -> None:
        for h in self.event_handlers:
            h.on_text_created(text)

    def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        self.assistant_snapshot += delta.value or ""
        for h in self.event_handlers:
            h.on_text_delta(delta, snapshot)

    def on_text_done(self, text: Text) -> None:
        for h in self.event_handlers:
            h.on_text_done(text)

    def on_tool_call_created(self, tool_call: ToolCall) -> None:
        for h in self.event_handlers:
            h.on_tool_call_created(tool_call)

    def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall) -> None:
        for h in self.event_handlers:
            h.on_tool_call_delta(delta, snapshot)

    def on_tool_call_done(self, tool_call: ToolCall) -> None:
        for h in self.event_handlers:
            h.on_tool_call_done(tool_call)

    def on_event(self, event: AssistantStreamEvent) -> None:
        for h in self.event_handlers:
            h.on_event(event)
        if event.event == "thread.run.requires_action":
            tool_outputs = []
            run_id = event.data.id
            for tool in self.tools:
                tool_outputs += tool.on_requires_action(event.data)
            if len(tool_outputs) > 0:
                new_runner_hanlder = RunnerHandler(self.event_handlers, self.tools)
                assert self.client
                assert self.current_run
                new_runner_hanlder.on_before_run(self.client)
                with self.client.beta.threads.runs.submit_tool_outputs_stream(
                    thread_id=self.current_run.thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs,
                    event_handler=new_runner_hanlder,
                ) as stream:
                    for text in stream.text_deltas:
                        pass
                self.assistant_snapshot += new_runner_hanlder.assistant_snapshot
                new_runner_hanlder.on_end_run()


class Runner:
    def __init__(self, runner_handler: RunnerHandler):
        self.client = create_client()
        self.handler = runner_handler

    def run_until_done(
        self,
        thread: Thread,
        assistant: Assistant,
        model: str | None = None,
        instructions: str | None = None,
        additional_instructions: str | None = None,
    ) -> str:
        self.handler.on_before_run(self.client)
        with self.client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant.id,
            model=model,
            instructions=instructions,
            additional_instructions=additional_instructions,
            tools=[i for s in [t.schemas for t in self.handler.tools] for i in s],
            event_handler=self.handler,
        ) as stream:
            stream.until_done()
        self.handler.on_end_run()
        return self.handler.assistant_snapshot


def chat(
    user: str,
    system: str = "You are a helpful assistant.",
    model: str = "gpt-4.5-preview",
    predication_in: str | None = None,
) -> str:
    client = openai.OpenAI(api_key=api.secret.openai_token)
    predication: ChatCompletionPredictionContentParam | openai.NotGiven = (
        openai.NOT_GIVEN
    )
    if predication_in is not None:
        predication = {"type": "content", "content": predication_in}
        model = "gpt-4o"
    result = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
        prediction=predication,
    )
    if predication and result.usage:
        api.log.info(
            f"model: {model}, completion_tokens_details: {result.usage.completion_tokens_details}"
        )
    return result.choices[0].message.content or ""


def generate_image(prompt: str, model: str = "dall-e-3") -> str:
    client = openai.OpenAI(api_key=api.secret.openai_token)
    result = client.images.generate(prompt=prompt, model=model, n=1, size="1024x1024")
    url = result.data[0].url
    if url:
        return api.publish.to_gyazo(requests.get(url).content)
    else:
        return "no image generated"
