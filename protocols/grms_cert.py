"""GRMS 监控协议 - 证书与升级类命令 (0x31-0x38)
证书请求、证书下发、固件升级
"""

GRMS_CERT_TEMPLATES = {
    # ===== 1.21 证书请求 (0x31/0x32) =====
    '证书请求(发送)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '31', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x31'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'CertType', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '证书类型: 0=设备证书, 1=平台证书', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 0, 'label': '设备证书'}, {'value': 1, 'label': '平台证书'}]},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 7, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS证书请求(发送)',
    },
    '证书请求(回复)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '32', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x32'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'Result', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '0=失败, 1=成功', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 0, 'label': '失败'}, {'value': 1, 'label': '成功'}]},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 7, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS证书请求(回复)',
    },
    # ===== 1.22 证书下发 (0x33/0x34) =====
    '证书下发(发送)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '33', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x33'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'CertDataLen', 'hex_value': '0010', 'byte_count': 2, 'field_type': '数据', 'description': '证书数据长度'},
            {'name': 'CertData', 'hex_value': '00000000000000000000000000000000', 'byte_count': 16, 'field_type': '数据', 'description': '证书数据'},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 8, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS证书下发(发送)',
    },
    '证书下发(回复)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '34', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x34'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'Result', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '0=失败, 1=成功', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 0, 'label': '失败'}, {'value': 1, 'label': '成功'}]},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 7, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS证书下发(回复)',
    },
    # ===== 1.23 固件升级 (0x35/0x36) =====
    '固件升级(发送)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '35', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x35'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'FirmwareLen', 'hex_value': '0010', 'byte_count': 2, 'field_type': '数据', 'description': '固件数据长度'},
            {'name': 'FirmwareData', 'hex_value': '00000000000000000000000000000000', 'byte_count': 16, 'field_type': '数据', 'description': '固件数据'},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 8, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS固件升级(发送)',
    },
    '固件升级(回复)': {
        'fields': [
            {'name': 'Header', 'hex_value': 'BA', 'byte_count': 1, 'field_type': '固定值', 'description': '命令头'},
            {'name': 'Func', 'hex_value': '36', 'byte_count': 1, 'field_type': '数据', 'description': '功能码 0x36'},
            {'name': 'Sequence', 'hex_value': '0001', 'byte_count': 2, 'field_type': '数据', 'description': '流水号'},
            {'name': 'Box', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'TotalLen', 'hex_value': '', 'byte_count': 2, 'field_type': '长度', 'description': '命令长度之和', 'length_start': 0, 'length_end': 3, 'length_byte_order': 'big'},
            {'name': 'DeviceCode', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备编码'},
            {'name': 'DeviceBox', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '设备地址'},
            {'name': 'Result', 'hex_value': '01', 'byte_count': 1, 'field_type': '数据', 'description': '0=失败, 1=成功', 'parse_mode': '枚举映射', 'enum_mappings': [{'value': 0, 'label': '失败'}, {'value': 1, 'label': '成功'}]},
            {'name': 'CRC16', 'hex_value': '', 'byte_count': 2, 'field_type': '校验', 'description': 'CRC16校验(高位在前)', 'checksum_algorithm': 'CRC16/MODBUS', 'checksum_start': 0, 'checksum_end': 7, 'checksum_byte_order': 'big'},
        ],
        'desc': 'GRMS固件升级(回复)',
    },
}
