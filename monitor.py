import mysql.connector
import time
import threading
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler
from watchdog.events import FileModifiedEvent
import os
import psutil

from utilites import StoppableThread, get_camip_v4, get_hostname
from config import app_config


class mem_monitor(StoppableThread):
    def __init__(self, *args, **kwargs):
        self._interval = kwargs['template']['interval']
        self._template = kwargs['template']
        self._msgs = kwargs['msgsqueue']
        self._logger = kwargs['logger']
        self._ev = threading.Event()
        super().__init__(*args)

    def run(self) -> None:
        self._logger.debug("mem monitor started..")
        wait_total = 0
        while not self.stopped():
            if wait_total < self._interval:
                self._ev.wait(1)
                wait_total += 1
                continue
            wait_total = 0
            percent = round(psutil.virtual_memory().available /
                            psutil.virtual_memory().total, 2)
            msg = {
                'version': self._template['version'],
                'log_type': self._template['log_type'],
                'log_subtype': self._template['log_subtype'],
                'log_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                'mem': "{}%".format(percent),
                'node_ip': get_camip_v4(),
                'node_hostname': get_hostname()
            }
            self._msgs.put(msg)
        self._logger.debug("mem monitor stopped..")
        return super().run()


class cpu_monitor(StoppableThread):
    def __init__(self, *args, **kwargs):
        self._interval = kwargs['template']['interval']
        self._template = kwargs['template']
        self._msgs = kwargs['msgsqueue']
        self._logger = kwargs['logger']
        self._ev = threading.Event()
        super().__init__(*args)

    def run(self) -> None:
        self._logger.debug("cpu monitor started..")
        wait_total = 0
        while not self.stopped():
            if wait_total < self._interval:
                self._ev.wait(1)
                wait_total += 1
                continue
            wait_total = 0
            percent = psutil.cpu_percent()
            if percent > 0:  # 没有使用率无意义
                msg = {
                    'version': self._template['version'],
                    'log_type': self._template['log_type'],
                    'log_subtype': self._template['log_subtype'],
                    'log_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    'cpu': "{}%".format(percent),
                    'node_ip': get_camip_v4(),
                    'node_hostname': get_hostname()
                }
                self._msgs.put(msg)
        self._logger.debug("cpu monitor stopped..")
        return super().run()


class file_monitor_handler(FileSystemEventHandler):
    # def on_any_event(self, event):
    #     print(event.event_type)

    def on_modified(self, event):

        if event.is_directory:  # 不处理目录改变
            return
        if not os.path.exists(event.src_path):  # 删除也会导致“修改”事件
            return
        else:
            # print(event.src_path, event.event_type)
            with self._lock:
                self._files.append(event.src_path)
                with self._cond:
                    self._cond.notify()

    def on_deleted(self, event):
        if not event.is_directory:
            print(event.src_path)
            print(event.event_type)

    def __init__(self, lock, cond, files) -> None:
        self._lock = lock
        self._files = files
        self._cond = cond
        super().__init__()


class file_monitor(StoppableThread):
    def __init__(self, *args, **kwargs):
        self._file_watch_handler = kwargs['handler']
        self._logger = kwargs['logger']
        self._file_map_watch = {}
        self.__observer = Observer()
        self._files_to_watch = []
        self._file_with_func = kwargs['file_2_func'][0]  # 正在监控的文件到功能的映射
        self._file_with_func_lock = kwargs['file_2_func'][1]
        super().__init__(*args)

    def run(self) -> None:
        self._logger.debug("file monitor started..")
        # self.__observer.start()
        while not self.stopped():
            files_to_watch = self.__get_files_to_watch__()
            diff = False
            for file in files_to_watch:
                if file not in self._files_to_watch:
                    diff = True
                    break
            if diff:
                self.__update_observer_schedule__(files_to_watch)

            time.sleep(1)
        self._logger.debug("file monitor ended..")
        self.__observer.unschedule_all()
        self._file_map_watch.clear()
        self._files_to_watch.clear()
        return super().run()

    def __get_files_to_watch__(self) -> dict:
        files_to_watch = {}
        for key in app_config['log'].keys():
            if 'file' not in app_config['log'][key]:
                continue
            file = app_config['log'][key]['file']
            try:
                file = eval(app_config['log'][key]['file'])
                files_to_watch[file] = key  # {"/tmp/zf" : "switch"}
            except NameError as e:
                pass
                # self._logger.debug(e)
            except Exception as e:
                pass
                # self._logger.debug(e)

        return files_to_watch

    def __update_observer_schedule__(self, new_files_to_watch) -> None:

        # 先删除不在监控列表的任务
        for file in self._files_to_watch:
            if file not in new_files_to_watch:
                if file in self._file_map_watch:
                    watch = self._file_map_watch[file]
                    self.__observer.unschedule(watch)
                    self._file_map_watch.pop(file)
                    with self._file_with_func_lock:
                        self._file_with_func[file]['fd'].close()  # 关闭文件描述符
                        self._file_with_func.pop(file)
                    self._logger.debug("remove watch:{}".format(file))

        # 再加入新的监控任务
        for file in new_files_to_watch:
            if file not in self._files_to_watch:
                if os.path.exists(file):  # 有些文件到时间点不生成怎么办？
                    watch = self.__observer.schedule(
                        self._file_watch_handler, file, recursive=False)
                    self._file_map_watch[file] = watch
                    with self._file_with_func_lock:
                        self._file_with_func[file] = {}
                        self._file_with_func[file]['func'] = new_files_to_watch[file]
                        self._file_with_func[file]['fd'] = open(file, 'r')
                        if 'keytext' in app_config['log'][new_files_to_watch[file]]:
                            self._file_with_func[file]['keytext'] = \
                                app_config['log'][new_files_to_watch[file]
                                                  ]['keytext']
                        if not self.__observer.is_alive():
                            self.__observer.start()
                    self._logger.debug("new watch:{}".format(file))
                else:
                    self._logger.debug("log file:{} not exists.".format(file))
        self._files_to_watch = new_files_to_watch


class database_monitor(StoppableThread):
    def __init__(self, *args, **kwargs):
        self._logger = kwargs['logger']
        self._db_conf = kwargs['db']
        super().__init__(*args)

    def run(self) -> None:
        # 读取记录的配置，如果没有，last设置为当前时间 TODO
        self._db_conf['last'] = time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime())

        conn = None

        try:
            count = 1
            while (conn is None or not conn.is_connected()) and not self.stopped():
                self._logger.debug(
                    "try to connect db {} times...".format(count))
                count += 1
                conn = mysql.connector.connect(host=self._db_conf['host'],
                                               database=self._db_conf['db'],
                                               user=self._db_conf['user'],
                                               password=self._db_conf['password'])
                if conn.is_connected():
                    break

                time.sleep(1)

        except Exception as e:
            self._logger.error(e)

        if conn is None or not conn.is_connected():
            self._logger.error('cannot Connected to MySQL database')
            return
        cursor = conn.cursor()

        while not self.stopped():
            cursor.execute("select * from {} where sentTime > \"{}\"".format(
                self._db_conf['table'], self._db_conf['last']))
            records = cursor.fetchall()
            for record in records:
                self._db_conf['last'] = record[8]
                print(self._db_conf['last'])
            count = 1
            while not self.stopped() and count < self._db_conf['interval']:
                time.sleep(1)
                count += 1

        if conn is not None and conn.is_connected():
            conn.close()

        return super().run()
