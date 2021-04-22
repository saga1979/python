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
        self._files_monified = kwargs['files']
        self._cond = kwargs['cond']
        self._logger = kwargs['logger']
        self._file_with_func = kwargs['file_2_func'][0]
        self._file_with_func_lock = kwargs['file_2_func'][1]
        super().__init__(*args)

    def run(self) -> None:
        self._logger.debug("parser service started..")

        # 根据日志中保存的最近一次记录确定要读取日志文件的位置 TODO
        last_reads_file = open(app_config['system']['lastread'], 'r')
        last_reads = last_reads_file.read()
        last_reads_file.close()
        try:
            last_read_obj = json.loads(last_reads)
        except json.decoder.JSONDecodeError as e:
            self._logger.error(e.msg)

        self._cond.acquire()
        while not self.stopped():
            if self._cond.wait(10):
                with self._lock:
                    for file in self._files_monified:
                        lines = self._file_with_func[file]['fd'].readlines()
                        for line in lines:
                            # 处理需要的日志信息
                            if self._file_with_func[file]['keytext'] in line:
                                self._logger.warning(
                                    "file:{} {}".format(file, "find key text!!!"))
                        if len(lines) > 0:
                            self._file_with_func[file]['last'] = lines[len(
                                lines) - 1]
                            self._file_with_func[file]['time'] = time.strftime(
                                '%Y-%m-%d %H:%M:%S', time.localtime())
                            self._logger.debug("{}'s last line is:\ {}".format(
                                file, self._file_with_func[file]['last']))
                        else:
                            self._logger.warning(
                                "{} read 0 lines!".format(file))

                    self._files_monified.clear()

        self._cond.release()
        # 写入更新后的文件配置 TODO

        last_read_obj = {}
        for key in self._file_with_func.keys():
            if 'last' not in self._file_with_func[key]:
                continue
            last_read_obj[self._file_with_func[key]['func']] = {
                'file': key,
                'last':  self._file_with_func[key]['last'],
                'time': self._file_with_func[key]['time']
            }

        with open(app_config['system']['lastread'], 'w') as last_read:
            last_read.write(json.dumps(last_read_obj))

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
