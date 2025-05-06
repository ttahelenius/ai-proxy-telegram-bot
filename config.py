import configparser
import json.decoder
import pathlib

_INTERNAL_SECTIONS = ["TelegramBot", "TextOverrides", "Extension"]

_config_file = pathlib.Path(__file__).parent.absolute().as_posix() + "/config.ini"

_config = configparser.ConfigParser()
_config.read(_config_file, encoding='utf-8')

_decoder = json.JSONDecoder()

def get(category: str, variable: str) -> str | None:
    if category not in _config or variable not in _config[category]:
        return None
    return _config[category][variable]

def get_boolean_or_false(category: str, variable: str) -> bool | None:
    if category not in _config or variable not in _config[category]:
        return False
    return _config[category][variable].lower() == "true"

def get_int(category: str, variable: str) -> int | None:
    if category not in _config or variable not in _config[category]:
        return None
    return int(_config[category][variable])

def get_int_list(category: str, variable: str) -> list[int] | None:
    if category not in _config or variable not in _config[category]:
        return None
    return [int(i) for i in _config[category][variable][1:-1:].split(",") if i]

def get_or_default(category: str, variable: str, default: str) -> str:
    value = get(category, variable)
    if value is None:
        return default
    return value

def get_or_throw(category: str, variable: str) -> str:
    value = get(category, variable)
    if value is None:
        raise RuntimeError("No configuration for " + category + "." + variable + " in " + _config_file)
    return value

def get_key_value_pairs(category: str, variable: str) -> dict[str, any]:
    key_value_pairs = get_or_default(category, variable, "").strip().split("\n")
    if key_value_pairs == [""]:
        return {}
    return {k: _decoder.decode(v) for k, v in [tuple(p.split(" ")) for p in key_value_pairs]}


class Configuration:
    def __init__(self, command: str, api: str, feature: str, model: str, url: str, token: str | None, stream: bool | None, params: dict[str, any]):
        self.command = command
        self.api = api
        self.feature = feature
        self.model = model
        self.url = url
        self.token = token
        self.stream = stream
        self.params = params

def read_query_implementations() -> list[Configuration]:
    implementations = []
    for command in _config.sections():
        if command in _INTERNAL_SECTIONS:
            continue
        implementations.append(Configuration(command,
                                             get_or_throw(command, "Api"),
                                             get_or_throw(command, "Feature"),
                                             get_or_throw(command, "Model"),
                                             get_or_throw(command, "Url"),
                                             get(command, "Token"),
                                             get_boolean_or_false(command, "Stream"),
                                             get_key_value_pairs(command, "Params")))
    return implementations