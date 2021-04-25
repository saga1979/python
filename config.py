import time
app_config = {
    "system": {
        "log": "/tmp/log_monitor.log",
        "lastread": './last_read.json'
    },
    "server": {
        "ip": "127.0.0.1",
        "port": 3333
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
        'interval': 5

    },
    "log": {
        "danger_op": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x01",
            'type': "table",
            'table': '_cmdalarm',
            'timecolumn': 8,
            'sessioncolumn': 15,
            'cmdcolumn': 16,
            'operatecolumn': 2,
        },
        "multi_login": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x02",
            'type': "file",
            "file": r"'/tmp/z{}'.format(time.strftime('%Y%m%d%M', time.localtime()))",
            "keytext": r"111"
        },
        "heartloss": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x03",
            'type': "file",
            "file": r"'/mnt/e/work/ruining/python/ha-log-{}.log'.format(time.strftime('%Y%m%d', time.localtime()))",
            "keytext": r"lost packet(s) for"

        },
        "session_start": {
            "version": 1,
            "log_type": "0x27",
            "log_subtype": "0x01",
            "timecolumn": 4,
            'type': "table",
            "table": r" 'session{}'.format(time.strftime('%Y%m%d', time.localtime())"
        },
        "session_end": {
            "version": 1,
            "log_type": "0x27",
            "log_subtype": "0x02",
            "timecolumn": 5,
            'type': "table",
            "table": r" 'session{}'.format(time.strftime('%Y%m%d', time.localtime())"
        },
        "switch": {
            "version": 1,
            "log_type": "0x28",
            "log_subtype": "0x01",
            'type': "file",
            "file": r"'/mnt/e/work/ruining/python/ha-log-{}.log'.format(time.strftime('%Y%m%d', time.localtime()))",
            "keytext": "foreign HA resource release completed"
        },
        "cpu": {
            "version": 1,
            "log_type": "0x28",
            "log_subtype": "0x02",
            'type': "system",
            "interval": 60
        },
        "ram": {
            "version": 1,
            "log_type": "0x28",
            "log_subtype": "0x03",
            'type': "system",
            "interval": 5
        }
    },
}
