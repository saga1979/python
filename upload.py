
import socket
from time import sleep
from utilites import StoppableThread

import threading


class upload_service(StoppableThread):
    # 初始化的时候读取配置
    def __init__(self, *args, **kwargs):
        self.e = threading.Event()

        self.msgs = kwargs['msgs']
        self._cond = kwargs['cond']
        self._lock = kwargs['lock']
        self._logger = kwargs['logger']
        self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._server = kwargs['server']
        return super().__init__()

    def run(self):
        try:
            self._client.connect((self._server['ip'], self._server['port']))
        except ConnectionRefusedError as e:
            self._logger.error(e.strerror)
        msgs_pool = []
        while not self.stopped():

            try:
                while not self.msgs.empty():
                    msg = self.msgs.get(timeout=5)
                    msgs_pool.append(msg)
                    self.msgs.task_done()

                for msg in msgs_pool:
                    self._logger.debug(msg)
                if len(msgs_pool) > 0:
                    msgs_pool.clear()
                self.e.wait(timeout=5)
            except KeyboardInterrupt:
                self.stop()
                return
