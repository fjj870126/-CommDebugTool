"""JSON 协议示例模板 - 供 JSON 查看器使用"""

JSON_TEMPLATES = {

    '温控器协议': {
        'set_temperature': {
            'desc': '设置目标温度',
            'json': '''{
    "cmd": "set_temp",
    "id": 1,
    "value": 25,
    "unit": "celsius"
}'''
        },
        'query_status': {
            'desc': '查询设备状态',
            'json': '''{
    "cmd": "query",
    "id": 1
}'''
        },
        'status_report': {
            'desc': '设备状态上报',
            'json': '''{
    "cmd": "report",
    "id": 1,
    "type": "temperature",
    "current_temp": 26.5,
    "target_temp": 25,
    "mode": "cool",
    "fan_speed": "auto",
    "enabled": true,
    "errors": null,
    "sensors": [
        {"id": "s1", "value": 26.5},
        {"id": "s2", "value": 27.1}
    ]
}'''
        },
    },

    'MQTT 设备影子': {
        'update_property': {
            'desc': '更新设备属性',
            'json': '''{
    "method": "update",
    "device_id": "dev_001",
    "timestamp": 1714800000,
    "properties": {
        "temperature": 26.5,
        "humidity": 60.2,
        "power": "on"
    }
}'''
        },
        'desired_state': {
            'desc': '期望状态下发',
            'json': '''{
    "method": "desired",
    "device_id": "dev_001",
    "desired": {
        "temperature": 24,
        "power": "off"
    },
    "version": 3
}'''
        },
    },

    'HTTP API 响应': {
        'success_response': {
            'desc': '成功响应',
            'json': '''{
    "code": 0,
    "message": "success",
    "data": {
        "id": 12345,
        "name": "设备A",
        "status": "online",
        "last_seen": "2026-05-05T12:00:00Z"
    }
}'''
        },
        'error_response': {
            'desc': '错误响应',
            'json': '''{
    "code": 4001,
    "message": "参数错误",
    "errors": [
        {"field": "temperature", "reason": "超出范围 0-50"},
        {"field": "mode", "reason": "不支持的模式"}
    ]
}'''
        },
        'pagination': {
            'desc': '分页列表',
            'json': '''{
    "code": 0,
    "data": {
        "page": 1,
        "page_size": 10,
        "total": 156,
        "items": [
            {"id": 1, "name": "设备1", "online": true},
            {"id": 2, "name": "设备2", "online": false}
        ]
    }
}'''
        },
    },

    'Modbus JSON 网关': {
        'read_holding': {
            'desc': '读保持寄存器',
            'json': '''{
    "slave": 1,
    "function": 3,
    "address": 0,
    "count": 10
}'''
        },
        'write_single': {
            'desc': '写单个寄存器',
            'json': '''{
    "slave": 1,
    "function": 6,
    "address": 100,
    "value": 1500
}'''
        },
        'gateway_response': {
            'desc': '网关响应',
            'json': '''{
    "slave": 1,
    "function": 3,
    "data": [0, 1500, 250, 18, 65535, 0, 100, 200, 50, 10],
    "count": 10,
    "status": "ok"
}'''
        },
    },

}
