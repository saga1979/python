import threading
import json
import psutil
import selectors
import time
import os
from utilites import StoppableThread
from config import app_config


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


class parser_service(threading.Thread):
    def __init__(self, lock, cond, files) -> None:
        self._lock = lock
        self._files_to_read = files
        self._cond = cond
        self._files_manager = {}
        super().__init__()

    def run(self) -> None:
        # 读取监控配置 TODO
        files_to_watch = []
        for key in app_config['log'].keys():
            if 'file' in app_config['log'][key] and os.path.exists(app_config['log'][key]['file']):
                files_to_watch.append(app_config['log'][key]['file'])
        for file in files_to_watch:
            self._files_manager[file] = {
                'fd': open(file, 'r'),
                'last': ""
            }
            pass
        # 根据日志中保存的最近一次记录确定要读取日志文件的位置 TODO
        last_reads = open(app_config['system']['lastread'], 'r').read()
        config_obj_json = json.loads(last_reads)

        this_thread = threading.current_thread()
        self._cond.acquire()
        while getattr(this_thread, "do_run", True):
            f = self._cond.wait(10)
            if f:
                with self._lock:
                    for file in self._files_to_read:
                        lines = self._files_manager[file]['fd'].readlines()
                        for line in lines:
                            # 处理需要的日志信息
                            print("read file:{} {}".format(file, line))
                        self._files_manager[file]['last'] = lines[len(
                            lines) - 1]
                        print("{} last line: {}".format(
                            file, self._files_manager[file]['last']))

                    self._files_to_read.clear()
            else:
                print('no file modified..')
        self._cond.release()
        # 写入更新后的文件配置 TODO
        config = open(app_config['system']['lastread'], 'w')

        config_obj_json = {}
        for key in self._files_manager.keys():
            config_obj_json[key] = self._files_manager[key]['last']

        config.write(json.dumps(config_obj_json))

        config.close()

        return super().run()


class monitor_by_selector(threading.Thread):
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
