
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
        self._server = kwargs['server']
        return super().__init__(*args)

    def run(self):
        try:
            self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
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
                    self.send(msg)
                if len(msgs_pool) > 0:
                    msgs_pool.clear()
                self.e.wait(timeout=5)
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                self._logger.error(e)
                self.stop()
        if not self._client is None:
            self._client.close()

    def send(self, msg):
        totalsent = 0
        while totalsent < len(msg):
            sent = self._client.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def is_socket_closed(self, sock: socket.socket) -> bool:
        try:
            # this will try to read bytes without blocking and also without removing them from buffer (peek only)
            data = sock.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
            if len(data) == 0:
                return True
        except BlockingIOError:
            return False  # socket is open and reading from it would block
        except ConnectionResetError:
            return True  # socket was closed for some other reason
        except Exception as e:
            self._logger.error(
                "unexpected exception when checking if a socket is closed")
            return False
        return False
