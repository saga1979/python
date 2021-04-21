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
            print(event.src_path, event.event_type)
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


class monitor_service(StoppableThread):
    def __init__(self, *args, **kwargs):
        self._file_watch_handler = kwargs['handler']
        self._logger = kwargs['logger']
        super().__init__(*args)

    def run(self) -> None:
        observer = Observer()
        # event_handler = LoggingEventHandler()
        # observer.schedule(event_handler, path, recursive=True)

        files_to_watch = []
        # 'file'内容可为描述规则，根据规则动态生成具体得文件名，此处为测试需要按文件名处理
        for key in app_config['log'].keys():
            if 'file' not in app_config['log'][key]:
                continue
            file = app_config['log'][key]['file']
            try:
                file = eval(app_config['log'][key]['file'])
            except NameError as e:
                self._logger.debug(e)
            except Exception as e:
                self._logger.debug(e)
            files_to_watch.append(file)

        for file in files_to_watch:
            self._logger.debug("watch:{}".format(file))
            if os.path.exists(file):
                watch = observer.schedule(
                    self._file_watch_handler, file, recursive=False)
                self._logger.debug("watch:{}".format(watch.path))

        observer.start()

    # observer.unschedule(watch)
        while not self.stopped():
            time.sleep(1)
        return super().run()

    def check(self) -> bool:
        new_day = time.localtime().tm_mday

        pass
