import importlib
import logging
from telebot.types import Message
from . import config


class ServiceRefuser:
    def refuse(self, msg: Message) -> bool:
        return False

def get_service_refuser() -> ServiceRefuser:
    extension = config.get("Extension", "ServiceRefuser")
    if extension is None:
        return ServiceRefuser()
    module = importlib.import_module(extension)
    return module.CustomServiceRefuser()


def setup_logging():
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    error_log = config.get("TelegramBot", "ErrorLog")
    if error_log:
        file_handler = logging.FileHandler(error_log)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

reply_logger = config.get("TelegramBot", "ReplyLog")

def log_reply(vendor: str, model: str, reply: str, chat_id: int):
    if reply_logger:
        loggable_chat_ids = config.get_int_list("TelegramBot", "ChatIDFilterForReplyLog")
        if loggable_chat_ids is not None and chat_id not in loggable_chat_ids:
            return
        with open(reply_logger, "a", encoding="utf-8") as f:
            f.write(vendor + " " + model + ":\n" + reply + "\n\n\n")