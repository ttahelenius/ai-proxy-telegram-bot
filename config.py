import configparser
import pathlib

_config_file = pathlib.Path(__file__).parent.absolute().as_posix() + "/config.ini"

_config = configparser.ConfigParser()
_config.read(_config_file, encoding='utf-8')

def get(category: str, variable: str) -> str | None:
    if category not in _config or variable not in _config[category]:
        return None
    return _config[category][variable]

def get_int(category: str, variable: str) -> int | None:
    if category not in _config or variable not in _config[category]:
        return None
    return int(_config[category][variable])

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