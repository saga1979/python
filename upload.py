
import socket
from time import sleep

try:
    import _thread as thread  # python 3中，将thread模块重命名为_thread
except ImportError:
    import dummy_thread as thread

import threading


class upload_thread(threading.Thread):
    # 初始化的时候读取配置
    def __init__(self, msgs):
        self.e = threading.Event()
        self.stop = False
        self.msgs = msgs
        return super().__init__()

    def run(self):
        msgs_pool = []
        while not self.stop:
            try:
                while not self.msgs.empty():
                    msg = self.msgs.get(timeout=5)
                    msgs_pool.append(msg)
                    self.msgs.task_done()

                for msg in msgs_pool:
                    print(msg)
                if len(msgs_pool) > 0:
                    msgs_pool.clear()
                self.e.wait(timeout=5)
            except KeyboardInterrupt:
                self.stop = True
                return
