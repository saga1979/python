import sys
import os
import fcntl
import socket
import threading
from config import app_config
import netifaces as ni
from netifaces import AF_INET, AF_INET6, AF_LINK, AF_PACKET, AF_BRIDGE


def get_hostname():
    return socket.gethostname()


def get_camip_v4():
    return ni.ifaddresses(app_config["cam"]["eth"]["name"])[AF_INET][app_config["cam"]["eth"]["index"]]['addr']


def get_camip_v6():
    return ni.ifaddresses(app_config["cam"]["eth"]["name"])[AF_INET6][app_config["cam"]["eth"]["index"]]['addr']


def instance_already_running(label="default"):

    lock_file_pointer = os.open(
        f"/tmp/instance_{label}.lock", os.O_WRONLY | os.O_CREAT)

    try:
        fcntl.lockf(lock_file_pointer, fcntl.LOCK_EX | fcntl.LOCK_NB)
        already_running = False
    except IOError:
        already_running = True

    return already_running


class StoppableThread(threading.Thread):

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
