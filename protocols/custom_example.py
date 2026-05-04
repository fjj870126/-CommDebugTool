"""自定义协议示例模板"""

CUSTOM_EXAMPLE_TEMPLATES = {
    '自定义协议示例': {
        '查询状态': {
            'fields': [
                {'name': '帧头', 'hex_value': 'AA', 'byte_count': 1, 'field_type': '固定值', 'description': '帧起始标志'},
                {'name': '命令', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '查询命令'},
                {'name': '数据', 'hex_value': '00', 'byte_count': 1, 'field_type': '数据', 'description': '保留'},
                {'name': '校验和', 'hex_value': '', 'byte_count': 1, 'field_type': '校验', 'description': '累加校验', 'checksum_start': 0, 'checksum_end': 2, 'checksum_byte_order': 'big'},
            ],
            'desc': '查询设备状态',
        },
        '设置参数': {
            'fields': [
                {'name': '帧头', 'hex_value': 'AA', 'byte_count': 1, 'field_type': '固定值', 'description': '帧起始标志'},
                {'name': '命令', 'hex_value': '02', 'byte_count': 1, 'field_type': '数据', 'description': '设置命令'},
                {'name': '参数值', 'hex_value': 'FF', 'byte_count': 1, 'field_type': '数据', 'description': '要设置的参数'},
                {'name': '校验和', 'hex_value': '', 'byte_count': 1, 'field_type': '校验', 'description': '累加校验', 'checksum_start': 0, 'checksum_end': 2, 'checksum_byte_order': 'big'},
            ],
            'desc': '设置设备参数',
        },
    },
}
