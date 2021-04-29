import json
import mysql.connector
import time
import threading
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler
from watchdog.events import FileModifiedEvent
import os
import psutil

from utilites import StoppableThread, get_camip_v4, get_camip_v6, get_hostname
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
        threshold = 0
        if 'threshold' in self._template:
            threshold = self._template['threshold']
        while not self.stopped():
            if wait_total < self._interval:
                self._ev.wait(1)
                wait_total += 1
                continue
            wait_total = 0
            percent = round(psutil.virtual_memory().available /
                            psutil.virtual_memory().total, 2)
            if percent >= threshold:
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
        threshold = 0
        if 'threshold' in self._template:
            threshold = self._template['threshold']
        while not self.stopped():
            if wait_total < self._interval:
                self._ev.wait(1)
                wait_total += 1
                continue
            wait_total = 0
            percent = psutil.cpu_percent()
            if percent > threshold:
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
            if 'enabled' in app_config['log'][key]:
                if not app_config['log'][key]['enabled']:
                    continue
            file = app_config['log'][key]['file']
            try:
                file = eval(app_config['log'][key]['file'])
                # 一个文件，多种功能
                if file in files_to_watch and key != files_to_watch[file][0]:
                    files_to_watch[file].append(key)
                elif file not in files_to_watch:
                    files_to_watch[file] = [key]  # {"/tmp/zf" : ["switch"]}
            except NameError as e:
                pass
                # self._logger.debug(e)
            except Exception as e:
                pass
                # self._logger.debug(e)
#        self._logger.debug(files_to_watch)
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
            if file in self._files_to_watch:
                continue
            if not os.path.exists(file):  # 有些文件到时间点不生成怎么办？
                self._logger.debug("log file:{} not exists.".format(file))
                continue

            watch = self.__observer.schedule(
                self._file_watch_handler, file, recursive=False)
            self._file_map_watch[file] = watch
            with self._file_with_func_lock:
                self._file_with_func[file] = {}
                functions = new_files_to_watch[file]
                self._file_with_func[file]['func'] = functions
                self._file_with_func[file]['fd'] = open(file, 'r')
                for function in functions:
                    if 'keytext' in self._file_with_func[file]:
                        self._file_with_func[file]['keytext'].append(
                            app_config['log'][function]['keytext'])
                    else:
                        self._file_with_func[file]['keytext'] = [
                            app_config['log'][function]['keytext']]
                if not self.__observer.is_alive():
                    self.__observer.start()
            self._logger.debug("new watch:{}".format(file))

        self._files_to_watch = new_files_to_watch
        # self._logger.debug("file to func:{}".format(self._file_with_func))


class database_monitor(StoppableThread):
    def __init__(self, *args, **kwargs):
        self._logger = kwargs['logger']
        self._db_conf = kwargs['db']
        self._msgs = kwargs['msgsqueue']
        self._template = kwargs['template']
        self._db_record = {}
        self._log_file = app_config['system']['db_last']
        super().__init__(*args)

    def run(self) -> None:
        # 读取记录的配置，如果没有，last设置为当前时间 TODO
        # self._db_conf['danger_op_last'] = time.strftime(
        #    '%Y-%m-%d %H:%M:%S', time.localtime())
        # 会话记录没有时间字段，TODO
        # self._db_conf['session_last'] = time.strftime(
        #    '%Y-%m-%d %H:%M:%S', time.localtime())
        """数据库按照记录索引定位，比如，会话记录就没有该条记录的产生时间

        """
        self._db_record['danger_op'] = {
            'last': 1
        }
        self._db_record['session'] = {
            'done': [],
            'todo': []
        }
        self._db_record['multi_login'] = {
            'last': 1
        }
        try:
            with open(self._log_file, 'r') as log_fd:
                self._db_record = json.load(log_fd)
        except FileNotFoundError as e:
            self._logger.warning(e)
        except json.decoder.JSONDecodeError as e:
            self._logger.warning(e)
        conn = None
        cursor = None
        while not self.stopped():
            try:
                func_enabled = False
                conn = mysql.connector.connect(host=self._db_conf['host'],
                                               database=self._db_conf['db'],
                                               user=self._db_conf['user'],
                                               password=self._db_conf['password'])
                if conn is None or not conn.is_connected():
                    time.sleep(1)
                    self._logger.warning("connect to database failed..")
                    continue

                cursor = conn.cursor()
                # cursor.execute("select * from {} where sentTime > \"{}\"".format(
                #     self._db_conf['table'], self._db_conf['last']))

                cursor.execute("select count(*) from _cmdalarm;")
                records = cursor.fetchall()

                if len(records) > 0:
                    alarm_count = records[0][0]
                    alarm_readed = self._db_record['danger_op']['last']
                    if alarm_count > alarm_readed:
                        cursor.execute("select * from _cmdalarm limit {},{}".format(
                            alarm_readed, alarm_count - alarm_readed))
                        records = cursor.fetchall()
                        # 更新已读取的记录索引
                        self._db_record['danger_op']['last'] = alarm_readed + \
                            len(records)
                        for record in records:
                            msg = {
                                'version': self._template['danger_op']['version'],
                                'log_type': self._template['danger_op']['log_type'],
                                'log_subtype': self._template['danger_op']['log_subtype'],
                                'log_time': record[self._template['danger_op']['timecolumn']],
                                'dev_name': get_hostname(),
                                'dev_ipv4': get_camip_v4(),
                                'dev_ipv6': get_camip_v6(),
                                'session_id': record[self._template['danger_op']['sessioncolumn']],
                                'action_id': record[self._template['danger_op']['cmdcolumn']],
                                'approvers': "",
                                'operate_content': record[self._template['danger_op']['operatecolumn']]

                            }
                            self._logger.debug("[database][op]:{}".format(msg))
                            self._msgs.put(msg)
                # 会话记录并没有时间可作为排序，因为完全有可能一个会话迟于其他会话开始，早于其他会话结束，或者其他情况
                # cursor.execute("select * from {} where ")
                session_table_name = "session{}".format(
                    time.strftime('%Y%m%d', time.localtime()))
                cursor.execute(
                    "select count(*) from {};".format(session_table_name))
                records = cursor.fetchall()

                if len(records) > 0:
                    alarm_count = records[0][0]
                    # sID_done = ",".join(
                    #     [elem for elem in self._db_record['session']['done']])
                    sID_done = ""
                    for sID in self._db_record['session']['done']:
                        if len(sID_done) == 0:
                            sID_done = r'"{}"'.format(sID)
                        else:
                            sID_done = r'{},"{}"'.format(sID_done, sID)

                    if len(sID_done) == 0:
                        sID_done = '\"\"'
                    sql = r"select * from {} where sID not in ({})".format(
                        session_table_name, sID_done)
                    cursor.execute(sql)
                    records = cursor.fetchall()
                    for record in records:
                        msg = []
                        if record[0] in self._db_record['session']['todo']:
                            # 只发送结束会话得日志
                            if record[5] is not None:  # 结束时间不为空，添加当前记录得sid到完成
                                self._db_record['session']['done'].append(
                                    record[0])
                                self._db_conf['session']['todo'].remove(
                                    record[0])
                        else:
                            if record[4] is not None and record[5] is not None:  # 既有开始又有结束
                                self._db_record['session']['done'].append(
                                    record[0])
                                msg.append({
                                    'version': self._template['session_start']['version'],
                                    'log_type': self._template['session_start']['log_type'],
                                    'log_subtype': self._template['session_start']['log_subtype'],
                                    'log_time': record[self._template['session_start']['timecolumn']],
                                    'dev_name': get_hostname(),
                                    'dev_ipv4': get_camip_v4(),
                                    'dev_ipv6': get_camip_v6(),
                                    'access_id': 0,
                                    'session_id': record[0],

                                    'resource_name': "",
                                    'resource_addr': "",
                                    "resource_port": 0,
                                    "resource_account": "",
                                    "resource_account_type": 1,
                                    "tool_name": record[12],
                                    "user_id": record[0],
                                    "user_name": record[1],
                                    "user_addr": "",
                                    "user_port": 0

                                })
                                msg.append({
                                    'version': self._template['session_end']['version'],
                                    'log_type': self._template['session_end']['log_type'],
                                    'log_subtype': self._template['session_end']['log_subtype'],
                                    'log_time': record[self._template['session_end']['timecolumn']],
                                    'dev_name': get_hostname(),
                                    'dev_ipv4': get_camip_v4(),
                                    'dev_ipv6': get_camip_v6(),
                                    'access_id': 0,
                                    'session_id': record[0],

                                    'resource_name': "",
                                    'resource_addr': "",
                                    "resource_port": 0,
                                    "resource_account": "",
                                    "resource_account_type": 1,
                                    "tool_name": record[12],
                                    "user_id": record[0],
                                    "user_name": record[1],
                                    "user_addr": "",
                                    "user_port": 0

                                })
                            elif record[4] is not None:  # 开始时间不为空，添加当前记录到待完成
                                self._db_conf['session']['todo'].append(
                                    record[0])
                                msg.append({
                                    'version': self._template['session_start']['version'],
                                    'log_type': self._template['session_start']['log_type'],
                                    'log_subtype': self._template['session_start']['log_subtype'],
                                    'log_time': record[self._template['session_start']['timecolumn']],
                                    'dev_name': get_hostname(),
                                    'dev_ipv4': get_camip_v4(),
                                    'dev_ipv6': get_camip_v6(),
                                    'access_id': 0,
                                    'session_id': record[0],

                                    'resource_name': "",
                                    'resource_addr': "",
                                    "resource_port": 0,
                                    "resource_account": "",
                                    "resource_account_type": 1,
                                    "tool_name": record[12],
                                    "user_id": record[0],
                                    "user_name": record[1],
                                    "user_addr": "",
                                    "user_port": 0

                                })
                        for sub_msg in msg:
                            self._logger.debug(
                                "[database][session]:{}".format(sub_msg))
                            self._msgs.put(sub_msg)
                # 多点登录处理
                multi_login_config = app_config['log']['multi_login']
                if "enabled" in multi_login_config:
                    func_enabled = multi_login_config["enabled"]
                if not func_enabled:
                    continue
                cursor.execute(
                    "select count(*) from {};".format(multi_login_config["table"]))
                records = cursor.fetchall()
                if len(records) <= 0:
                    continue
                record_count = records[0][0]
                record_readed = self._db_record['multi_login']['last']

                if record_count <= record_readed:
                    continue
                cursor.execute("select * from {} limit {},{}".format(
                    multi_login_config["table"], record_readed, record_count - record_readed))
                records = cursor.fetchall()
                # 更新已读取的记录索引
                self._db_record['multi_login']['last'] = alarm_readed + \
                    len(records)
                for record in records:
                    msg = {
                        'version': self._template['multi_login']['version'],
                        'log_type': self._template['multi_login']['log_type'],
                        'log_subtype': self._template['multi_login']['log_subtype'],
                        'log_time': record[self._template['multi_login']['timecolumn']],
                        'dev_name': get_hostname(),
                        'dev_ipv4': get_camip_v4(),
                        'dev_ipv6': get_camip_v6(),
                        'user_id': record[self._template['multi_login']['user_id']],
                        'user_name': record[self._template['multi_login']['user_name']],
                        'user_addr': record[self._template['multi_login']['user_addr']]

                    }
                    self._logger.debug("[database][multi]:{}".format(msg))
                    self._msgs.put(msg)

            except mysql.connector.errors.ProgrammingError as e:
                self._logger.warning(e)
            finally:
                if cursor is not None:
                    cursor.close()
                if conn is not None and conn.is_connected():
                    conn.close()
                count = 1
                while not self.stopped() and count < self._db_conf['interval']:
                    time.sleep(1)
                    count += 1

        # 将缓存记录写入文件
        with open(self._log_file, 'w') as log_fd:
            log_fd.write(json.dumps(self._db_record))
