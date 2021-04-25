import threading
import json
import psutil
import selectors
import time
import datetime
import os
from utilites import StoppableThread, get_camip_v4, get_camip_v6, get_hostname
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


class file_parser_service(StoppableThread):
    def __init__(self, *args, **kwargs):
        self._lock = kwargs['lock']
        self._files_monified = kwargs['files']
        self._cond = kwargs['cond']
        self._logger = kwargs['logger']
        self._file_with_func = kwargs['file_2_func'][0]
        self._file_with_func_lock = kwargs['file_2_func'][1]
        self._msgs = kwargs['msgsqueue']
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
            if not self._cond.wait(10):
                continue

            with self._lock:
                for file in self._files_monified:
                    fd = self._file_with_func[file]['fd']
                    """ 这个地方可以优化
                    只需要记录准备切换时的位置,标识字符串：
                    Apr 09 12:58:28 camha1 ipfail: [4632]: info: giveup() called (timeout worked)
                    Apr 09 12:58:28 camha1 heartbeat: [3981]: info: camha1 wants to go standby [foreign]
                    Apr 09 12:58:29 camha1 heartbeat: [3981]: info: standby: camha2 can take our foreign resources
                    """
                    pos = fd.tell()
                    failover_action = 2  # 主备切换类型
                    has_switch = False
                    has_switch_last_datetime = None
                    has_loss = False
                    has_loss_last_datetime = None
                    msgs = []
                    while True:
                        line = fd.readline()
                        if len(line) == 0:
                            break
                        fields = line.split()

                        if "wants to go standby" in line:  # 双机互备开始的标识符,这地方要记录，否则无法判断切换类型
                            pos = fd.tell()
                        elif "camha2 can take our foreign resources" in line:  # "切换动作，1：到备机 2：到主机",
                            failover_action = 1
                        elif "remote resource transition completed" in line:  # 切换完成

                            pos = fd.tell()
                            the_datetime_str = '{} {} {} {}'.format(time.localtime().tm_year,
                                                                    fields[0], fields[1], fields[2])
                            the_datetime = datetime.datetime.strptime(the_datetime_str,
                                                                      '%Y % b % d % H: % M: % S')
                            if has_switch_last_datetime >= the_datetime:
                                continue
                            has_switch = True
                            msg = {
                                'version': app_config['log']['switch']['version'],
                                'log_type': app_config['log']['switch']['log_type'],
                                'log_subtype': app_config['log']['switch']['log_subtype'],
                                'log_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                'failover_action': failover_action,  # "切换动作，1：到备机 2：到主机",
                                'active_node_ip': get_camip_v4(),
                                'active_node_hostname': get_hostname(),
                            }
                            msgs.append(msg)

                        elif "lost packet(s) for" in line:
                            """心跳丢失
                            可能出现在双机切换过程中，所以需要记住其时间，避免文件指针回退的时候重复读取
                            """

                            pos = fd.tell()
                            the_datetime_str = '{} {} {} {}'.format(time.localtime().tm_year,
                                                                    fields[0], fields[1], fields[2])
                            the_datetime = datetime.datetime.strptime(the_datetime_str,
                                                                      '%Y % b % d % H: % M: % S')

                            if has_loss_last_datetime >= the_datetime:  # 就是已经记录过
                                continue

                            has_loss = True
                            has_loss_last_datetime = the_datetime

                            msg = {
                                'version': app_config['log']['heartloss']['version'],
                                'log_type': app_config['log']['heartloss']['log_type'],
                                'log_subtype': app_config['log']['heartloss']['log_subtype'],
                                'log_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                'dev_ipv4': get_camip_v4(),
                                'dev_name': get_hostname(),
                                'dev_ipv6': get_camip_v6(),
                                'heartloss_node_ip': "",  # 日志信息缺少，但是否可以通过主机名获取IP？
                                "heartloss_node_hostname": fields[fields.index('for') + 1]
                            }
                            msgs.append(msg)

                    for msg in msgs:
                        self._msgs.put(msg)
                        self._logger.debug("create msg:{}".format(msg))

                    if len(msgs) == 0:  # 如果没有需要的记录，要回退文件指针
                        fd.seek(pos)

                    # lines = fd.readlines()

                    # for line in lines:
                    #     if "camha2 can take our foreign resources" in line:
                    #         failover_action = 1  # 到备机
                    #     # 处理需要的日志信息
                    #     for index in range(len(self._file_with_func[file]['keytext'])):
                    #         if self._file_with_func[file]['keytext'][index] not in line:
                    #             continue
                    #         # 根据不同的功能对应的json模板生成消息
                    #         for func in self._file_with_func[file]['func']:
                    #             msg = {}
                    #             if 'heartloss' in func:  # 心跳丢失
                    #                 fields = line.split()

                    #                 msg = {
                    #                     'version': app_config['log'][func]['version'],
                    #                     'log_type': app_config['log'][func]['log_type'],
                    #                     'log_subtype': app_config['log'][func]['log_subtype'],
                    #                     'log_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    #                     'dev_ipv4': get_camip_v4(),
                    #                     'dev_name': get_hostname(),
                    #                     'dev_ipv6': get_camip_v6(),
                    #                     'heartloss_node_ip': "",
                    #                     "heartloss_node_hostname": fields[fields.index('for') + 1]
                    #                 }
                    #             elif 'switch' in func:  # 双机切换
                    #                 msg = {
                    #                     'version': app_config['log'][func]['version'],
                    #                     'log_type': app_config['log'][func]['log_type'],
                    #                     'log_subtype': app_config['log'][func]['log_subtype'],
                    #                     'log_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    #                     'failover_action': failover_action,  # "切换动作，1：到备机 2：到主机",
                    #                     'active_node_ip': get_camip_v4(),
                    #                     'active_node_hostname': get_hostname(),
                    #                 }
                    #                 pass
                    #             if len(msg) > 0:
                    #                 self._msgs.put(msg)
                    #             else:
                    #                 fd.seek(pos)
                    #             self._logger.warning(
                    #                 "file:{} find :{}".format(file, self._file_with_func[file]['keytext'][index]))
                    # if len(lines) > 0:  # 应该判断一下，如果没有发现要报警的信息怎么办？TODO
                    #     self._file_with_func[file]['last'] = lines[len(
                    #         lines) - 1]
                    #     self._file_with_func[file]['time'] = time.strftime(
                    #         '%Y-%m-%d %H:%M:%S', time.localtime())
                    #     self._logger.debug("{}'s last line is:\ {}".format(
                    #         file, self._file_with_func[file]['last']))
                    # else:
                    #     self._logger.warning(
                    #         "{} read 0 lines!".format(file))

                self._files_monified.clear()

        self._cond.release()
        # 写入更新后的文件配置 TODO

        last_read_obj = {}
        for key in self._file_with_func.keys():
            if 'last' not in self._file_with_func[key]:
                continue
            # 其实多个功能使用同一个文件时，记录一个功能的最后读取文本就行了
            for func in self._file_with_func[key]['func']:
                last_read_obj[func] = {
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
