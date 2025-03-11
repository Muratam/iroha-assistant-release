# how to set up

`vim iroha/api/secret.py`

```
response_slack_channel_id = "C..."
response_debug_slack_channel_id = "C..."

# tokens
slack_token = "xoxp-..."
openai_token = "sk-..."
gyazo_token = "..."
perplexity_token="pplx-..."

# pathes
publish_path_prefix = "https://..."
local_path_prefix = "..."

# iroha assistant
openai_iroha_assistant_id = "asst_..."
openai_temporary_assistant_id = "asst_..."
```

`cp -r /path/to/assets/ ./assets`

# how to run

```sh
# run slack bot
./run.sh

# run script
./run.sh iroha/scripts/chatgpt.py "Hello World"
```
