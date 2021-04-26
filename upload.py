
import json
import socket
from time import sleep
import time

from mysql.connector import connect
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
        # load cache msgs from disk cache file ? TODO
        msgs_pool = []
        queue_max = self._server['queue']['max']
        is_cache = self._server['queue']['cache']
        is_log = self._server['queue']['log'][0]
        reconnect_interval = self._server['reconn']
        self._client = None
        while not self.stopped():
            connected = True
            if self.is_socket_closed(self._client):
                try:
                    self._client = socket.socket(
                        socket.AF_INET, socket.SOCK_STREAM, 0)
                    self._client.connect(
                        (self._server['ip'], self._server['port']))
                    self._logger.info("connected to server!")
                except ConnectionRefusedError as e:
                    sleeped = 0
                    connected = False
                    self._logger.debug(
                        "try reconnect server after {} seconds".format(reconnect_interval))
                    while not self.stopped() and sleeped < reconnect_interval:
                        time.sleep(1)
                        sleeped += 1
            if not connected:
                continue
            try:
                while not self.msgs.empty():
                    msg = self.msgs.get(timeout=5)
                    msgs_pool.append(msg)
                    self.msgs.task_done()
                # if send msg failed, or msgs pool size than 1000, write cache to disk file?TODO

                for msg in msgs_pool:
                    self._logger.debug(msg)
                    self.send(msg)
                    with open(eval(self._server['queue']['log'][1]), 'a+') as log_file:
                        json.dump(msg, log_file)
                msgs_pool.clear()
                self.e.wait(timeout=5)
            except KeyboardInterrupt:
                self.stop()
            except RuntimeError as e:
                self._logger.error(e)
            except Exception as e:
                self._logger.error(e)
        if not self._client is None:
            self._client.close()
        self._logger.warning("upload service ended....")

    def send(self, msg):
        totalsent = 0
        msg_to_send = json.dumps(msg).encode('UTF-8')
        while totalsent < len(msg_to_send):
            sent = self._client.send(msg_to_send[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def is_socket_closed(self, sock: socket.socket) -> bool:
        if sock is None:
            return True
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
            self._logger.warning(e)
            return True
        return False
