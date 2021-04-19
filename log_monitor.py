

import sys
import time
import logging
import queue
import signal
import argparse
import os
import json
import logging
import threading

from pathlib import Path
from upload import upload_thread
from watchdog.observers import Observer

from parser import heart_lost, monitor, parser_monitor, file_monitor_handler


import utilites
from config import app_config

# import socket
# import time
# client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

# client.connect(("localhost", 3333))

# while True:
#     client.send(b"hello python")

#     msg = client.recv(1024)
#     print(msg.decode())
#     time.sleep(1)


def keyboardInterruptHandler(signal, frame):
    print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(signal))
    exit(0)


def msgProvider(msgs, msg):
    ev = threading.Event()
    while True:
        msgs.put(msg)
        ev.wait(timeout=5)


monitors = {}


def parsers_init():
    monitors['/tmp/zf'] = {
        'file': '/tmp/zf',
        'cond': threading.Condition()
    }


if __name__ == "__main__":
    # condition test

    # parsers_init()

    # heart =  heart_lost(monitors['/tmp/zf'])

    # heart.start()
    # heart.join()

    # 参数解析
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-c", "--config", help="config file path")
    arg_parser.add_argument("-v", "--version", action='store_true')
    args = arg_parser.parse_args()
    if args.config:
        try:
            config_file = os.open(args.config, os.O_RDONLY)
            config_str = os.read(config_file, 2048).decode("utf-8")
            os.close(config_file)
            app_config = json.loads(config_str)
        except OSError as e:
            print("{0} open failed because :\n{1}!".format(
                args.config, e.strerror))
        except json.decoder.JSONDecodeError as e:
            print(e)

        # 初始化配置
    logging.basicConfig(format='[%(asctime)s] [%(levelname)s]:%(message)s',
                        filename=app_config['system']['log'], level=logging.DEBUG)

    app_config["cam"]["eth"]["name"] = 'lo'
    logging.debug(utilites.get_camip_v4())

    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else '.'

    observer = Observer()
    # event_handler = LoggingEventHandler()
    # observer.schedule(event_handler, path, recursive=True)

    file = '/tmp/zf'
    lock = threading.Lock()
    cond = threading.Condition()
    files = []

    if Path(file).is_file():
        watch = observer.schedule(file_monitor_handler(
            lock, cond, files), file, recursive=False)
        print("watch:", watch.path)

        observer.start()
    else:
        print('file not exists')
    # observer.unschedule(watch)

    # 日志上传
    # msgs = queue.Queue()
    # upload = upload_thread(msgs)
    # upload.start()

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
