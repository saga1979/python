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


class parser_service(StoppableThread):
    def __init__(self, *args, **kwargs):
        self._lock = kwargs['lock']
        self._files_to_read = kwargs['files']
        self._cond = kwargs['cond']
        self._logger = kwargs['logger']
        self._files_manager = {}
        super().__init__(*args)

    def run(self) -> None:
        self._logger.debug("parser service started..")
        # 读取监控配置 TODO
        for key in app_config['log'].keys():

            if 'file' not in app_config['log'][key]:
                continue
            file = app_config['log'][key]['file']
            if not os.path.exists(file):
                continue
            self._files_manager[app_config['log'][key]['file']] = {
                'fd': open(file, 'r'),
                'type': key,
                'last': "",
                'time': ""
            }

        # 根据日志中保存的最近一次记录确定要读取日志文件的位置 TODO
        last_reads_file = open(app_config['system']['lastread'], 'w+')
        last_reads = last_reads_file.read()
        try:
            last_read_obj = json.loads(last_reads)
        except json.decoder.JSONDecodeError as e:
            self._logger.error(e.msg)

        self._cond.acquire()
        while not self.stopped():
            if self._cond.wait(10):
                with self._lock:
                    for file in self._files_to_read:
                        lines = self._files_manager[file]['fd'].readlines()
                        for line in lines:
                            # 处理需要的日志信息
                            print("read file:{} {}".format(file, line))
                        self._files_manager[file]['last'] = lines[len(
                            lines) - 1]
                        self._files_manager[file]['time'] = time.strftime(
                            '%Y-%m-%d %H:%M:%S', time.localtime())
                        print("{} last line: {}".format(
                            file, self._files_manager[file]['last']))

                    self._files_to_read.clear()

        self._cond.release()
        # 写入更新后的文件配置 TODO

        last_read_obj = {}
        for key in self._files_manager.keys():
            last_read_obj[self._files_manager[key]['type']] = {
                'file': key,
                'last':  self._files_manager[key]['last'],
                'time': self._files_manager[key]['time']
            }

        last_reads_file.write(json.dumps(last_read_obj))

        last_reads_file.close()
        self._logger.debug("parser service ended..")
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
