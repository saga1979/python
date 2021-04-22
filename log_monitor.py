

from re import template
import sys
import time
import logging
import queue
import signal
import argparse
import os
import json
import logging
import coloredlogs
import threading

from pathlib import Path
from upload import upload_service
from watchdog.observers import Observer

from parser import heart_lost,  parser_service


from utilites import *
from config import app_config
from monitor import cpu_monitor, file_monitor_handler, monitor_service, mem_monitor


def keyboardInterruptHandler(signal, frame):
    mylogs.debug(
        "KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(signal))
    exit(0)


monitors = {}
# 待发送信息
msgs_to_send = queue.Queue()
msgs_to_send_lock = threading.Lock()
msgs_to_send_cond = threading.Condition()

if __name__ == "__main__":
    # 日志配置
    logging.basicConfig(format='[%(asctime)s] [%(levelname)s]:%(message)s',
                        level=logging.DEBUG)

    mylogs = logging.getLogger(__name__)
    coloredlogs.install(level=logging.DEBUG, logger=mylogs)

    file = logging.FileHandler(app_config['system']['log'])
    fileformat = logging.Formatter(
        '[%(asctime)s] [%(levelname)s]:%(message)s', datefmt="%H:%M:%S")
    file.setFormatter(fileformat)
    mylogs.addHandler(file)

    # 检查是否已有该程序实例在运行
    if instance_already_running():
        mylogs.warning("another instance already running...")
        exit(-1)
    # 信号处理
    signal.signal(signal.SIGINT, keyboardInterruptHandler)
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
            mylogs.error("{0} open failed because :\n{1}!".format(
                args.config, e.strerror))
        except json.decoder.JSONDecodeError as e:
            mylogs.error(e)

    # 初始化配置

    # 从配置创建任务

    app_config["cam"]["eth"]["name"] = 'lo'
    logging.debug(get_camip_v4())

    files_readable_lock = threading.Lock()
    files_readable_cond = threading.Condition()
    files_readable = []

    file_handler = file_monitor_handler(
        files_readable_lock, files_readable_cond, files_readable)

    file_to_func = {}
    file_to_func_lock = threading.Lock()

    # 文件监控服务
    monitorservice = monitor_service(handler=file_handler,
                                     file_2_func=(
                                         file_to_func, file_to_func_lock),
                                     logger=mylogs)
    monitorservice.start()

    # 文件解析服务
    parserservice = parser_service(lock=files_readable_lock,
                                   cond=files_readable_cond,
                                   files=files_readable,
                                   file_2_func=(
                                       file_to_func, file_to_func_lock),
                                   logger=mylogs)
    parserservice.start()
    # 内存监控
    memmonitor = mem_monitor(msgsqueue=msgs_to_send,
                             template=app_config['log']['ram'], logger=mylogs)
    memmonitor.start()
    # CPU监控
    cpumonitor = cpu_monitor(msgsqueue=msgs_to_send,
                             template=app_config['log']['cpu'], logger=mylogs)
    cpumonitor.start()
    # 信息发送服务
    uploadservice = upload_service(
        msgs=msgs_to_send, lock=msgs_to_send_lock,
        cond=msgs_to_send_cond, logger=mylogs, server=app_config['server'])
    uploadservice.start()
    try:
        while True:
            time.sleep(1)
    finally:
        cpumonitor.stop()
        memmonitor.stop()
        monitorservice.stop()
        parserservice.stop()
        uploadservice.stop()

        monitorservice.join()
        parserservice.join()
        uploadservice.join()
        memmonitor.join()
        cpumonitor.join()
