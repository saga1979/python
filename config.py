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
    "log": {
        "danger_op": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x01",
            "file": '/tmp/zf1'

        },
        "multi_login": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x02",
            "file": '/tmp/zf2'
        },
        "heart_lost": {
            "version": 1,
            "log_type": "0x26",
            "log_subtype": "0x03",
            "file": '/tmp/zf3'
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
            "file": '/tmp/zf6'
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
