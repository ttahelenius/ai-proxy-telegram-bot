import atexit
import importlib
import logging
import os
import pathlib
import signal
import sys
from time import sleep
import warnings
import subprocess
from telebot.types import Message
import config


class ServiceRefuser:
    def refuse(self, msg: Message):
        return False

def get_service_refuser() -> ServiceRefuser:
    extension = config.get("Extension", "ServiceRefuser")
    if extension is None:
        return ServiceRefuser()
    module = importlib.import_module(extension)
    return module.CustomServiceRefuser()


def override_background_instance_temporarily(main_file):
        lock = pathlib.Path(__file__).parent.absolute().as_posix() + "/running.lock"

        if "--test" in sys.argv:
            try:
                import psutil
                with open(lock, 'r') as f:
                    pid = int(f.read())
                    if psutil.pid_exists(pid):
                        try:
                            os.kill(pid, signal.SIGTERM)
                            while psutil.pid_exists(pid):
                                sleep(1)

                            atexit.register(lambda: _restart_background_instance(main_file))
                        except PermissionError:
                            pass
            except ImportError:
                warnings.warn("Background process interception not available", stacklevel=2)
        else:
            with open(lock, 'w') as f:
                f.write(str(os.getpid()))


def _restart_background_instance(main_file):
    subprocess.Popen([sys.executable, main_file], creationflags=subprocess.DETACHED_PROCESS)

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