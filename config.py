import time
app_config = {
    "system": {
        "log": "/tmp/log_monitor.log",
        "lastread": './last_read.json'
    },
    "server": {
        "ip": "127.0.0.1",
        "port": 888
    },
    "cam": {
        "eth": {
            "name": "eth0",
            "index": 0
        }

    },
    "database": {
        'type': "mysql",
        'host': '10.0.0.2',
        'user': 'saga',
        'password': '123456',
        'db': 'test',
        'table': '_cmdalarm',
        'timecolumn': 8,
        'sessioncolumn': 15,
        'cmdcolumn': 16,
        'operatecolumn': 2,
        'interval': 5

    },
    "log": {
        "danger_op": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x01",
        },
        "multi_login": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x02",
            "file": r"'/tmp/z{}'.format(time.strftime('%Y%m%d%M', time.localtime()))",
            "keytext": r"111"
        },
        "heartloss": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x03",
            "file": r"'/mnt/e/work/ruining/python/ha-log-{}.log'.format(time.strftime('%Y%m%d', time.localtime()))",
            "keytext": r"lost packet(s) for"

        },
        "session_start": {
            "version": 1,
            "log_type": "0x27",
            "log_subtype": "0x01",
            "file": '/tmp/zf4'
        },
        "session_end": {
            "version": 1,
            "log_type": "0x27",
            "log_subtype": "0x02",
            "file": '/tmp/zf5'
        },
        "switch": {
            "version": 1,
            "log_type": "0x28",
            "log_subtype": "0x01",
            "file": r"'/mnt/e/work/ruining/python/ha-log-{}.log'.format(time.strftime('%Y%m%d', time.localtime()))",
            "keytext": "foreign HA resource release completed"
        },
        "cpu": {
            "version": 1,
            "log_type": "0x28",
            "log_subtype": "0x02",
            "interval": 60
        },
        "ram": {
            "version": 1,
            "log_type": "0x28",
            "log_subtype": "0x03",
            "interval": 5
        }
    },
}
