# **Telegram Bot as a Proxy for AI**

This is a bot for [Telegram](https://telegram.org/), to be used as a proxy for various AI systems.
The bot relays messages to the AI and back via an easy to configure and extensible interface,
and attempts to format the result as best it can.

Currently supported text to text and image to text models for:
* [OpenAI API](https://openai.com/api/)
* [Ollama](https://ollama.com/) [local API](https://github.com/ollama/ollama?tab=readme-ov-file#rest-api)

The implementation uses [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) to
set up the Telegram bot and help with the formatting, and [requests](https://github.com/psf/requests) to streamline HTTP request logic.

## **Getting Started**

### **Installation**

```bash
git clone https://github.com/ttahelenius/ai-proxy-telegram-bot.git
```

Install the dependencies: [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) and [requests](https://github.com/psf/requests)
```bash
pip install pyTelegramBotAPI
pip install requests
```

> [!NOTE]
> Python 3.9+ required.

<br />

### **Usage**

1. Obtain a [Telegram bot token](https://core.telegram.org/bots/features#creating-a-new-bot),
2. configure access to HTTP APIs of the AI systems of choice,
3. create [config.ini](#configuration) based on these, and
4. run:
    ```bash
    Python -m AIProxyTelegramBot.main
    ```

<br />

### **Example**

With the following `config.ini`...
```ini
[TelegramBot]
Token = {your-telegram-bot-token}

[gpt]
Api = OpenAI
Feature = Text gen
Url = https://api.openai.com/v1/chat/completions
Token = {your-open-ai-token}
Model = gpt-4o
Stream = true
```
...one could ask in the presence of the bot:
```plaintext
gpt Why is the sky blue?
```

<br />

### **Configuration**

A `config.ini` file should be created in the project root:

```ini
[TelegramBot]
Token = {your-telegram-bot-token}
MaxMessagesPerReply = 3
ErrorLog = error_log_for_daemonized_instance.txt
ReplyLog = reply_log_for_debugging_formatting.txt
ChatIDFilterForReplyLog = [1234567890, -9876543210]
ChatIDFilterForPersistentHistory = [1234567890, -9876543210]

[message-prefix-ai-will-respond-to-in-telegram]
Feature = Text gen
Api = OpenAI|Ollama
Url = ai-api-endpoint-url
Model = ai-model-alias
Token = ai-api-key
Stream = True|False
Params =
    api_extra_param1 9999
    api_extra_param2 "string"

[Extension]
ServiceRefuser = custom.python_module

[TextOverrides]
PleaseWait = Placeholder for first message before AI response
ToBeContinued = Placeholder for subsequent messages if response is split
ThatsEnough = MaxMessagesPerReply reached
EmptyReply = The response was empty for whatever reason
Thinking = Caption for the <think>...</think> part in R1 response
ServiceRefused = Message denoting service refusal as per ServiceRefuser
PossibleOtherTextStrings = As defined in texts.py
```

> [!NOTE]
> The only required parameter is `Token` in `[TelegramBot]`.
> Otherwise missing configurations will be ignored and their respective features deactivated.
> Any number of AI configurations allowed, each responding to their own commands.
> Changes in the config will activate at the next run.

The features configured herein are documented in detail [here](#Features).

<br />

## **Features**

* Responds to the following, sent or edited:
  * Messages as prompts of the form described in [Usage](#Usage).
  * Photos sent with the caption as prompt (for vision models).
  * Photos or stickers replied to, with the message as prompt (for vision models).
* Replied to messages (from others than the bot itself) are sent as quotation in the prompt.
* Streaming: On text output, the bot sends a message first and edits it as new tokens get generated.
* Conversation history: by replying to the bot's message (any of them), the reply as well as all
  previous replied to messages, will constitute message history that the bot will be aware of.
  > :information_source:
    The history only exists for the lifetime of the instance (bot messages sent beforehand will be
    ignored if replied to), **unless** relevant `ChatIDFilterForPersistentHistory` parameter has been
    configured. Each model has its own noninterchangeable history.

  > :warning: The previous messages may contribute to the token count in the AI, increasing the
    costs for premium AI services.
* Works around the limits of Telegram:
  * if the result is larger than allowed in one message,
    it'll be split into multiple replies.
  * Bot cooldowns will be avoided by only updating messages
    when allowed (meanwhile streaming).
* Formatting: LLMs seem to prefer formatting the output in MarkDown and LaTeX so these
  are supported in the bot insofar as it's possible (e.g. headings require a bit of creativity as there's
  no equivalent in [Telegram's version of MarkDown](https://core.telegram.org/bots/api#markdownv2-style)).
  LaTeX formatting is possible if the package [pylatexenc](https://github.com/phfaist/pylatexenc) is installed
  (albeit the bot will function without it); LaTeX code is then interpreted as Unicode characters.
* Extendability:
  * API details: `config.ini` allows for any API address and model, as well as an arbitrary number of additional parameters.
  * Adding support for a new API: subclasses for `Query` in [query](query.py) can be implemented with customizable:
    * input writing by overriding `get_data` and `history_printer`
    * output reading by overriding `get_response_text`
    * output formatting via the constructor parameter `formatter`
  * ServiceRefuser: a `config.ini` parameter pointing to a Python file implementing the interface
    `ServiceRefuser` in [util](util.py), for refusing service for arbitrary criteria.
  * Language: Each output text can be customized in `config.ini` to say whatever instead, in any language.
* Debugging features:
  * `ErrorLog` in `config.ini`
  * `ReplyLog` in `config.ini` records each response in raw text for debugging the formatting.
    The parameter `ChatIDFilterForReplyLog` can be used to limit this to only certain chats.
  * Possible errors are sent as messages. If an error occurred during the parsing of the response,
    the response is sent as is.