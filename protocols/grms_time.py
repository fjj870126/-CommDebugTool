"""GRMS 监控协议 - 校时与授权类命令 (0x09-0x0E)
普通校时、NTP校时、调试授权
"""

GRMS_TIME_TEMPLATES = {
    # ===== 1.6 普通校时 (0x09/0x0A) =====
    '普通校时(发送)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '09', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x09'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'YEAR', 'hex_value': '19', 'byte_count': 1, 'field_type': '数据', 'description': '年低位(年高位默认20), 0x19=25即2025年'},
            {'name': 'MONTH', 'hex_value': '0A', 'byte_count': 1, 'field_type': '数据', 'description': '月, 0x0A=10月'},
            {'name': 'DAY', 'hex_value': '0E', 'byte_count': 1, 'field_type': '数据', 'description': '日, 0x0E=14日'},
            {'name': 'WEEK', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '星期 [1-7], 0x01=周一'},
            {'name': 'HOUR', 'hex_value': '0E', 'byte_count': 1, 'field_type': '数据', 'description': '时, 0x0E=14时'},
            {'name': 'MINUTE', 'hex_value': '2F', 'byte_count': 1, 'field_type': '数据', 'description': '分, 0x2F=47分'},
            {'name': 'SECOND', 'hex_value': '13', 'byte_count': 1, 'field_type': '数据', 'description': '秒, 0x13=19秒'},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 13, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS普通校时(发送)',
    },
    '普通校时(回复)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '0A', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x0A'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'Result', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '0=失败, 1=成功', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 0, 'label': '失败'}, {'value': 1, 'label': '成功'}]},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 7, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS普通校时(回复)',
    },
    # ===== 1.7 NTP校时 (0x0B/0x0C) =====
    'NTP校时(发送)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '0B', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x0B'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'NTP_IP', 'hex_value': 'C0A80101', 'byte_count': 4, 'field_type': '数据', 'description': 'NTP服务器IP地址'},
            {'name': 'NTP_Port', 'hex_value': '007B', 'byte_count': 2, 'field_type': '数据', 'description': 'NTP服务器端口, 默认123(0x007B)'},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 8, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS NTP校时(发送)',
    },
    'NTP校时(回复)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '0C', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x0C'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'Result', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '0=失败, 1=成功', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 0, 'label': '失败'}, {'value': 1, 'label': '成功'}]},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 7, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS NTP校时(回复)',
    },
    # ===== 1.8 调试授权 (0x0D/0x0E) =====
    '调试授权(发送)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '0D', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x0D'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'AuthCode', 'hex_value': '00000000', 'byte_count': 4, 'field_type': '数据', 'description': '授权码'},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 7, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS调试授权(发送)',
    },
    '调试授权(回复)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '0E', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x0E'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'Result', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '0=失败, 1=成功', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 0, 'label': '失败'}, {'value': 1, 'label': '成功'}]},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 7, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS调试授权(回复)',
    },
}
