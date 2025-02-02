import atexit
import os
import pathlib
import signal
import sys
from time import sleep
import warnings
import subprocess

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