"""JSON 协议示例模板 - 内置 JSON 协议示例"""

JSON_TEMPLATES = {
    'JSON设备协议': {
        '上报状态': {
            'type': 'json',
            'fields': [
                {'key': 'device_id', 'type': 'string', 'required': True, 'default': 'SN001', 'description': '设备ID'},
                {'key': 'status', 'type': 'string', 'required': True, 'default': 'online', 'enum': ['online', 'offline', 'error'], 'description': '设备状态'},
                {'key': 'temperature', 'type': 'number', 'required': True, 'default': 25.0, 'minimum': -40, 'maximum': 125, 'description': '温度'},
                {'key': 'humidity', 'type': 'number', 'required': False, 'default': 50.0, 'minimum': 0, 'maximum': 100, 'description': '湿度'},
                {'key': 'battery', 'type': 'integer', 'required': False, 'default': 100, 'minimum': 0, 'maximum': 100, 'description': '电量'},
                {'key': 'error_code', 'type': 'integer', 'required': False, 'default': 0, 'minimum': 0, 'maximum': 999, 'description': '错误码'},
            ],
            'example': '{"device_id":"SN001","status":"online","temperature":26.5,"humidity":60,"battery":85,"error_code":0}',
            'desc': '设备上报状态信息',
        },
        '下发指令': {
            'type': 'json',
            'fields': [
                {'key': 'cmd', 'type': 'string', 'required': True, 'default': 'reboot', 'enum': ['reboot', 'update', 'config', 'query'], 'description': '指令类型'},
                {'key': 'device_id', 'type': 'string', 'required': True, 'default': 'SN001', 'description': '目标设备ID'},
                {'key': 'params', 'type': 'object', 'required': False, 'default': {}, 'description': '指令参数'},
                {'key': 'timeout', 'type': 'integer', 'required': False, 'default': 30, 'minimum': 1, 'maximum': 300, 'description': '超时时间'},
            ],
            'example': '{"cmd":"reboot","device_id":"SN001","params":{"delay":5},"timeout":30}',
            'desc': '下发控制指令到设备',
        },
        '配置更新': {
            'type': 'json',
            'fields': [
                {'key': 'cmd', 'type': 'string', 'required': True, 'default': 'config', 'enum': ['config'], 'description': '指令类型'},
                {'key': 'device_id', 'type': 'string', 'required': True, 'default': 'SN001', 'description': '设备ID'},
                {'key': 'config', 'type': 'object', 'required': True, 'default': {}, 'description': '配置参数'},
                {'key': 'version', 'type': 'string', 'required': False, 'default': '1.0', 'pattern': r'^\d+\.\d+$', 'description': '配置版本号'},
            ],
            'example': '{"cmd":"config","device_id":"SN001","config":{"interval":60,"threshold":30},"version":"1.0"}',
            'desc': '更新设备配置参数',
        },
        '告警通知': {
            'type': 'json',
            'fields': [
                {'key': 'type', 'type': 'string', 'required': True, 'default': 'critical', 'enum': ['alert', 'warning', 'critical'], 'description': '告警类型'},
                {'key': 'device_id', 'type': 'string', 'required': True, 'default': 'SN001', 'description': '设备ID'},
                {'key': 'message', 'type': 'string', 'required': True, 'default': '告警信息', 'description': '告警信息'},
                {'key': 'level', 'type': 'integer', 'required': True, 'default': 1, 'minimum': 1, 'maximum': 5, 'description': '告警等级'},
                {'key': 'timestamp', 'type': 'integer', 'required': False, 'default': 0, 'description': '时间戳'},
            ],
            'example': '{"type":"critical","device_id":"SN001","message":"温度过高","level":5,"timestamp":1700000000}',
            'desc': '设备告警通知',
        },
    },
    'JSON传感网络': {
        '传感器数据': {
            'type': 'json',
            'fields': [
                {'key': 'sensor_id', 'type': 'string', 'required': True, 'default': 'SENSOR_001', 'pattern': r'^SENSOR_\d+$', 'description': '传感器ID'},
                {'key': 'data_type', 'type': 'string', 'required': True, 'default': 'temperature', 'enum': ['temperature', 'pressure', 'flow', 'level'], 'description': '数据类型'},
                {'key': 'value', 'type': 'number', 'required': True, 'default': 23.5, 'description': '采集值'},
                {'key': 'unit', 'type': 'string', 'required': False, 'default': '', 'description': '单位'},
                {'key': 'quality', 'type': 'integer', 'required': False, 'default': 100, 'minimum': 0, 'maximum': 100, 'description': '信号质量'},
            ],
            'example': '{"sensor_id":"SENSOR_001","data_type":"temperature","value":23.5,"unit":"°C","quality":95}',
            'desc': '传感器采集数据上报',
        },
        '控制指令': {
            'type': 'json',
            'fields': [
                {'key': 'sensor_id', 'type': 'string', 'required': True, 'default': 'SENSOR_001', 'description': '传感器ID'},
                {'key': 'action', 'type': 'string', 'required': True, 'default': 'calibrate', 'enum': ['calibrate', 'reset', 'enable', 'disable'], 'description': '控制动作'},
                {'key': 'parameters', 'type': 'object', 'required': False, 'default': {}, 'description': '控制参数'},
            ],
            'example': '{"sensor_id":"SENSOR_001","action":"calibrate","parameters":{"offset":0.5}}',
            'desc': '传感器控制指令',
        },
    },
}
