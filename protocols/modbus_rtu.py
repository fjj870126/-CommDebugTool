"""Modbus RTU 协议模板"""

MODBUS_RTU_TEMPLATES = {
    'Modbus RTU': {
        '03 读保持寄存器': {
            'fields': [
                {'name': '从站地址', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '1-247'},
                {'name': '功能码', 'hex_value': '03', 'byte_count': 1, 'field_type': '数据', 'description': '读保持寄存器', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 1, 'label': '读线圈状态'}, {'value': 2, 'label': '读离散输入'}, {'value': 3, 'label': '读保持寄存器'}, {'value': 4, 'label': '读输入寄存器'}, {'value': 5, 'label': '写单个线圈'}, {'value': 6, 'label': '写单个寄存器'}, {'value': 15, 'label': '写多个线圈'}, {'value': 16, 'label': '写多个寄存器'}]},
                {'name': '起始地址', 'hex_value': '0000', 'byte_count': 2, 'field_type': '数据', 'description': '寄存器起始地址'},
                {'name': '寄存器数量', 'hex_value': '000A', 'byte_count': 2, 'field_type': '数据', 'description': '读取数量'},
            ],
            'desc': '读取从站保持寄存器数据',
        },
        '06 写单个寄存器': {
            'fields': [
                {'name': '从站地址', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '1-247'},
                {'name': '功能码', 'hex_value': '06', 'byte_count': 1, 'field_type': '数据', 'description': '写单个寄存器', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 1, 'label': '读线圈状态'}, {'value': 2, 'label': '读离散输入'}, {'value': 3, 'label': '读保持寄存器'}, {'value': 4, 'label': '读输入寄存器'}, {'value': 5, 'label': '写单个线圈'}, {'value': 6, 'label': '写单个寄存器'}, {'value': 15, 'label': '写多个线圈'}, {'value': 16, 'label': '写多个寄存器'}]},
                {'name': '寄存器地址', 'hex_value': '0000', 'byte_count': 2, 'field_type': '数据', 'description': '要写入的寄存器地址'},
                {'name': '数据值', 'hex_value': '00FF', 'byte_count': 2, 'field_type': '数据', 'description': '要写入的数据'},
            ],
            'desc': '写入单个寄存器值',
        },
        '10 写多个寄存器': {
            'fields': [
                {'name': '从站地址', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '1-247'},
                {'name': '功能码', 'hex_value': '10', 'byte_count': 1, 'field_type': '数据', 'description': '写多个寄存器', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 1, 'label': '读线圈状态'}, {'value': 2, 'label': '读离散输入'}, {'value': 3, 'label': '读保持寄存器'}, {'value': 4, 'label': '读输入寄存器'}, {'value': 5, 'label': '写单个线圈'}, {'value': 6, 'label': '写单个寄存器'}, {'value': 15, 'label': '写多个线圈'}, {'value': 16, 'label': '写多个寄存器'}]},
                {'name': '起始地址', 'hex_value': '0000', 'byte_count': 2, 'field_type': '数据', 'description': '起始寄存器地址'},
                {'name': '寄存器数量', 'hex_value': '0002', 'byte_count': 2, 'field_type': '数据', 'description': '写入数量'},
                {'name': '字节数', 'hex_value': '04', 'byte_count': 1, 'field_type': '数据', 'description': '数据字节数'},
                {'name': '数据', 'hex_value': '00010002', 'byte_count': 4, 'field_type': '数据', 'description': '要写入的数据'},
            ],
            'desc': '写入多个连续寄存器',
        },
        '01 读线圈状态': {
            'fields': [
                {'name': '从站地址', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '1-247'},
                {'name': '功能码', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '读线圈状态', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 1, 'label': '读线圈状态'}, {'value': 2, 'label': '读离散输入'}, {'value': 3, 'label': '读保持寄存器'}, {'value': 4, 'label': '读输入寄存器'}, {'value': 5, 'label': '写单个线圈'}, {'value': 6, 'label': '写单个寄存器'}, {'value': 15, 'label': '写多个线圈'}, {'value': 16, 'label': '写多个寄存器'}]},
                {'name': '起始地址', 'hex_value': '0000', 'byte_count': 2, 'field_type': '数据', 'description': '线圈起始地址'},
                {'name': '线圈数量', 'hex_value': '0008', 'byte_count': 2, 'field_type': '数据', 'description': '读取数量'},
            ],
            'desc': '读取从站线圈状态',
        },
        '05 写单个线圈': {
            'fields': [
                {'name': '从站地址', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '1-247'},
                {'name': '功能码', 'hex_value': '05', 'byte_count': 1, 'field_type': '数据', 'description': '写单个线圈', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 1, 'label': '读线圈状态'}, {'value': 2, 'label': '读离散输入'}, {'value': 3, 'label': '读保持寄存器'}, {'value': 4, 'label': '读输入寄存器'}, {'value': 5, 'label': '写单个线圈'}, {'value': 6, 'label': '写单个寄存器'}, {'value': 15, 'label': '写多个线圈'}, {'value': 16, 'label': '写多个寄存器'}]},
                {'name': '线圈地址', 'hex_value': '0000', 'byte_count': 2, 'field_type': '数据', 'description': '线圈地址'},
                {'name': '数据值', 'hex_value': 'FF00', 'byte_count': 2, 'field_type': '数据', 'description': 'FF00=ON, 0000=OFF', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 0x0000, 'label': 'OFF'}, {'value': 0xFF00, 'label': 'ON'}]},
            ],
            'desc': '写入单个线圈通断状态',
        },
    },
}
