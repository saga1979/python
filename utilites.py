import socket
from config import app_config
import netifaces as ni
from netifaces import AF_INET, AF_INET6, AF_LINK, AF_PACKET, AF_BRIDGE


def get_hostname():
    return socket.gethostname()


def get_camip_v4():
    return ni.ifaddresses(app_config["cam"]["eth"]["name"])[AF_INET][app_config["cam"]["eth"]["index"]]['addr']


def get_camip_v6():
    return ni.ifaddresses(app_config["cam"]["eth"]["name"])[AF_INET6][app_config["cam"]["eth"]["index"]]['addr']
