"""Modbus TCP 协议模板"""

MODBUS_TCP_TEMPLATES = {
    'Modbus TCP': {
        '03 读保持寄存器': {
            'fields': [
                {'name': '事务标识', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '事务处理标识'},
                {'name': '协议标识', 'hex_value': '0000', 'byte_count': 2, 'field_type': '固定值', 'description': '0=Modbus协议'},
                {'name': '长度', 'hex_value': '0006', 'byte_count': 2, 'field_type': '长度', 'description': '后续字节长度', 'length_start': 0, 'length_end': 1, 'length_byte_order': 'big'},
                {'name': '单元标识', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '从站地址'},
                {'name': '功能码', 'hex_value': '03', 'byte_count': 1, 'field_type': '数据', 'description': '读保持寄存器', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 1, 'label': '读线圈状态'}, {'value': 2, 'label': '读离散输入'}, {'value': 3, 'label': '读保持寄存器'}, {'value': 4, 'label': '读输入寄存器'}, {'value': 5, 'label': '写单个线圈'}, {'value': 6, 'label': '写单个寄存器'}, {'value': 15, 'label': '写多个线圈'}, {'value': 16, 'label': '写多个寄存器'}]},
                {'name': '起始地址', 'hex_value': '0000', 'byte_count': 2, 'field_type': '数据', 'description': '寄存器起始地址'},
                {'name': '寄存器数量', 'hex_value': '000A', 'byte_count': 2, 'field_type': '数据', 'description': '读取数量'},
            ],
            'desc': 'Modbus TCP 读保持寄存器',
        },
        '06 写单个寄存器': {
            'fields': [
                {'name': '事务标识', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '事务处理标识'},
                {'name': '协议标识', 'hex_value': '0000', 'byte_count': 2, 'field_type': '固定值', 'description': '0=Modbus协议'},
                {'name': '长度', 'hex_value': '0006', 'byte_count': 2, 'field_type': '长度', 'description': '后续字节长度', 'length_start': 0, 'length_end': 1, 'length_byte_order': 'big'},
                {'name': '单元标识', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '从站地址'},
                {'name': '功能码', 'hex_value': '06', 'byte_count': 1, 'field_type': '数据', 'description': '写单个寄存器', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 1, 'label': '读线圈状态'}, {'value': 2, 'label': '读离散输入'}, {'value': 3, 'label': '读保持寄存器'}, {'value': 4, 'label': '读输入寄存器'}, {'value': 5, 'label': '写单个线圈'}, {'value': 6, 'label': '写单个寄存器'}, {'value': 15, 'label': '写多个线圈'}, {'value': 16, 'label': '写多个寄存器'}]},
                {'name': '寄存器地址', 'hex_value': '0000', 'byte_count': 2, 'field_type': '数据', 'description': '要写入的寄存器地址'},
                {'name': '数据值', 'hex_value': '00FF', 'byte_count': 2, 'field_type': '数据', 'description': '要写入的数据'},
            ],
            'desc': 'Modbus TCP 写单个寄存器',
        },
        '01 读线圈状态': {
            'fields': [
                {'name': '事务标识', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '事务处理标识'},
                {'name': '协议标识', 'hex_value': '0000', 'byte_count': 2, 'field_type': '固定值', 'description': '0=Modbus协议'},
                {'name': '长度', 'hex_value': '0006', 'byte_count': 2, 'field_type': '长度', 'description': '后续字节长度', 'length_start': 0, 'length_end': 1, 'length_byte_order': 'big'},
                {'name': '单元标识', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '从站地址'},
                {'name': '功能码', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '读线圈状态', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 1, 'label': '读线圈状态'}, {'value': 2, 'label': '读离散输入'}, {'value': 3, 'label': '读保持寄存器'}, {'value': 4, 'label': '读输入寄存器'}, {'value': 5, 'label': '写单个线圈'}, {'value': 6, 'label': '写单个寄存器'}, {'value': 15, 'label': '写多个线圈'}, {'value': 16, 'label': '写多个寄存器'}]},
                {'name': '起始地址', 'hex_value': '0000', 'byte_count': 2, 'field_type': '数据', 'description': '线圈起始地址'},
                {'name': '线圈数量', 'hex_value': '0008', 'byte_count': 2, 'field_type': '数据', 'description': '读取数量'},
            ],
            'desc': 'Modbus TCP 读线圈状态',
        },
    },
}
