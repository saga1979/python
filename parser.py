import threading
import json
import psutil
import selectors
import time
import os

from pathlib import Path

from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler
from watchdog.events import FileModifiedEvent


class mem_monitor(threading.Thread):
    pass


class cpu_monitor(threading.Thread):
    pass


class heart_lost(threading.Thread):
    def __init__(self, mon):
        print(mon)
        self._cond = mon['cond']
        self._file = open(mon['file'])
        super().__init__()

    def run(self):
        self._cond.acquire()
        while True:

            can_read = self._cond.wait(10)
            if can_read:
                content = self._file.readlines()
                print(content)
            else:
                print('waited 10 seconds...')
        self._cond.release()
        # return super().run()


class file_monitor_handler(FileSystemEventHandler):
    # def on_any_event(self, event):
    #     print(event.event_type)

    def on_modified(self, event):
        if event.is_directory:  # 不处理目录改变
            return
        if not Path(event.src_path).is_file():  # 删除也会导致“修改”事件
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


class parser_service(threading.Thread):
    def __init__(self, lock, cond, files) -> None:
        self._lock = lock
        self._files_to_read = files
        self._cond = cond
        self._stop = False
        super().__init__()

    def run(self) -> None:
        # 读取要监控的文件配置 TODO

        self._cond.acquire()
        while not self._stop:
            f = self._cond.wait(10)
            if f:
                with self._lock:
                    for file in self._files_to_read:
                        print(file)
                    self._files_to_read.clear()
            else:
                print('no file modified..')
        self._cond.release()
        # 写入更新后的文件配置 TODO
        return super().run()


class monitor(threading.Thread):
    def __init__(self):
        self._sel = selectors.SelectSelector()
        self._f = open('/tmp/zf', 'r')
        self._f.readlines()
        # os.set_blocking(self._f.fileno(), False)
        self._sel.register(self._f, selectors.EVENT_READ, '/tmp/zf')
        super().__init__()

    def run(self):
        while True:
            events = self._sel.select(5)

            for key, mask in events:
                print("read from {}".format(key.data))

                print(key.fileobj.readlines())
            time.sleep(2)
