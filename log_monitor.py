import sys
import time
import logging
import queue
import signal
import argparse
import json
import coloredlogs
import threading
import atexit

from pathlib import Path
from upload import upload_service
from watchdog.observers import Observer

from parser import heart_lost,  file_parser_service


from utilites import *
from config import app_config
from monitor import cpu_monitor, file_monitor_handler, file_monitor, mem_monitor, database_monitor


def keyboardInterruptHandler(signal, frame):
    mylogs.debug(
        "KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(signal))

    sys.exit()


def app_exit():
    with open(app_config['system']['app_config'], 'w') as app_config_fd:
        app_config_fd.write(json.dumps(app_config, indent=4))
    pass


monitors = {}
# 待发送信息
msgs_to_send = queue.Queue()
msgs_to_send_lock = threading.Lock()
msgs_to_send_cond = threading.Condition()

if __name__ == "__main__":
    # 日志配置
    logging.basicConfig(format='[%(asctime)s] {%(filename)s:%(lineno)d} [%(levelname)s]:%(message)s',
                        level=logging.DEBUG)

    mylogs = logging.getLogger(__name__)
    coloredlogs.install(level=logging.DEBUG, logger=mylogs,
                        fmt='[%(asctime)s] {%(module)s:%(funcName)s:%(lineno)d} [%(levelname)s]:%(message)s')

    file = logging.FileHandler(app_config['system']['log'])
    fileformat = logging.Formatter(
        '[%(asctime)s] {%(pathname)s:%(lineno)d} [%(levelname)s]:%(message)s', datefmt="%Y-%m-%D %H:%M:%S")
    file.setFormatter(fileformat)
    mylogs.addHandler(file)

    # 检查是否已有该程序实例在运行
    if instance_already_running():
        mylogs.warning("another instance already running...")
        exit(-1)
    # 信号处理
    signal.signal(signal.SIGINT, keyboardInterruptHandler)
    atexit.register(app_exit)
    # 参数解析
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-c", "--config", help="config file path")
    arg_parser.add_argument("-v", "--version", action='store_true')
    arg_parser.add_argument("-d", "-D", help="run as a daemon",
                            action="store_true")
    args = arg_parser.parse_args()
    if args.d:
        print("run as daemon..todo...")
        pass  # run as deamon, TODO
    if args.config:
        try:
            with open(args.config, 'r') as config_fd:
                app_config = json.load(config_fd)
        except OSError as e:
            mylogs.error("{0} open failed because :\n{1}!".format(
                args.config, e.strerror))
        except json.decoder.JSONDecodeError as e:
            mylogs.error(e)
    else:
        try:
            with open(app_config['system']['app_config'], 'w') as config_fd:
                config_fd.write(json.dumps(app_config, indent=4))
        except OSError as e:
            mylogs.error("{0} open failed because :\n{1}!".format(
                args.config, e.strerror))

    # 初始化配置

    # 从配置创建任务

    files_readable_lock = threading.Lock()
    files_readable_cond = threading.Condition()
    files_readable = []

    file_handler = file_monitor_handler(
        files_readable_lock, files_readable_cond, files_readable)

    file_to_func = {}
    file_to_func_lock = threading.Lock()

    # 文件监控服务
    monitorservice = file_monitor(handler=file_handler,
                                  file_2_func=(
                                      file_to_func, file_to_func_lock),
                                  logger=mylogs)
    monitorservice.start()

    # 文件解析服务
    parserservice = file_parser_service(lock=files_readable_lock,
                                        cond=files_readable_cond,
                                        files=files_readable,
                                        msgsqueue=msgs_to_send,
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

    # 数据库监控
    dbmonitor = database_monitor(template={
        'danger_op': app_config['log']['danger_op'],
        'session_start': app_config['log']['session_start'],
        'session_end': app_config['log']['session_end']},
        msgsqueue=msgs_to_send, logger=mylogs, db=app_config['database'])
    dbmonitor.start()
    # 信息发送服务
    uploadservice = upload_service(
        msgs=msgs_to_send, lock=msgs_to_send_lock,
        cond=msgs_to_send_cond, logger=mylogs, server=app_config['server'])
    uploadservice.start()
    try:
        while True:
            time.sleep(1)
    finally:
        dbmonitor.stop()
        cpumonitor.stop()
        memmonitor.stop()
        monitorservice.stop()
        parserservice.stop()
        uploadservice.stop()

        dbmonitor.join()
        monitorservice.join()
        parserservice.join()
        uploadservice.join()
        memmonitor.join()
        cpumonitor.join()
