"""组包构建器 - 支持字段命名、自动校验计算、长度自动计算、模板保存/加载"""

import json
from packet.checksum import calc_checksum, get_algorithm_names, get_algorithm_width
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str


# 字段类型常量
FIELD_TYPE_FIXED = '固定值'
FIELD_TYPE_DATA = '数据'
FIELD_TYPE_LENGTH = '长度'
FIELD_TYPE_CHECKSUM = '校验'

FIELD_TYPES = [FIELD_TYPE_FIXED, FIELD_TYPE_DATA, FIELD_TYPE_LENGTH, FIELD_TYPE_CHECKSUM]


class PacketField:
    """数据包字段"""

    def __init__(self, name: str, hex_value: str, byte_count: int,
                 field_type: str = FIELD_TYPE_DATA,
                 length_start: int = 0, length_end: int = 0,
                 length_byte_order: str = 'big',
                 checksum_algorithm: str = 'CRC16/MODBUS',
                 checksum_start: int = 0, checksum_end: int = 0,
                 checksum_byte_order: str = 'big',
                 description: str = ''):
        self.name = name
        self.hex_value = hex_value.upper().replace(' ', '')
        self.byte_count = byte_count
        self.field_type = field_type
        # hex 值的含义说明
        self.description = description
        # 长度字段专用: 各自独立的计算范围
        self.length_start = length_start
        self.length_end = length_end
        self.length_byte_order = length_byte_order
        # 校验字段专用: 各自独立的校验配置
        self.checksum_algorithm = checksum_algorithm
        self.checksum_start = checksum_start
        self.checksum_end = checksum_end
        self.checksum_byte_order = checksum_byte_order

    def get_bytes(self) -> bytes:
        """获取字段的字节数据"""
        if not self.hex_value:
            return b'\x00' * self.byte_count
        try:
            data = hex_str_to_bytes(self.hex_value)
            if len(data) < self.byte_count:
                data = b'\x00' * (self.byte_count - len(data)) + data
            elif len(data) > self.byte_count:
                data = data[-self.byte_count:]
            return data
        except ValueError:
            return b'\x00' * self.byte_count

    def get_hex_display(self) -> str:
        """获取用于显示的hex字符串"""
        if self.field_type in (FIELD_TYPE_CHECKSUM, FIELD_TYPE_LENGTH):
            return '(自动)'
        return bytes_to_hex_str(self.get_bytes())

    def to_dict(self) -> dict:
        d = {
            'name': self.name,
            'hex_value': self.hex_value,
            'byte_count': self.byte_count,
            'field_type': self.field_type,
            'description': self.description,
        }
        if self.field_type == FIELD_TYPE_LENGTH:
            d['length_start'] = self.length_start
            d['length_end'] = self.length_end
            d['length_byte_order'] = self.length_byte_order
        if self.field_type == FIELD_TYPE_CHECKSUM:
            d['checksum_algorithm'] = self.checksum_algorithm
            d['checksum_start'] = self.checksum_start
            d['checksum_end'] = self.checksum_end
            d['checksum_byte_order'] = self.checksum_byte_order
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'PacketField':
        return cls(
            d['name'], d['hex_value'], d['byte_count'], d['field_type'],
            length_start=d.get('length_start', 0),
            length_end=d.get('length_end', 0),
            length_byte_order=d.get('length_byte_order', 'big'),
            checksum_algorithm=d.get('checksum_algorithm', 'CRC16/MODBUS'),
            checksum_start=d.get('checksum_start', 0),
            checksum_end=d.get('checksum_end', 0),
            checksum_byte_order=d.get('checksum_byte_order', 'big'),
            description=d.get('description', ''),
        )


class PacketBuilder:
    """数据包构建器"""

    def __init__(self):
        self.fields: list[PacketField] = []
        # 校验配置
        self.checksum_algorithm: str = 'CRC16/MODBUS'
        self.checksum_start: int = 0
        self.checksum_end: int = 0
        self.checksum_byte_order: str = 'big'

    def add_field(self, field: PacketField):
        self.fields.append(field)

    def insert_field(self, index: int, field: PacketField):
        self.fields.insert(index, field)

    def remove_field(self, index: int):
        if 0 <= index < len(self.fields):
            self.fields.pop(index)

    def move_field_up(self, index: int):
        if 0 < index < len(self.fields):
            self.fields[index], self.fields[index - 1] = \
                self.fields[index - 1], self.fields[index]

    def move_field_down(self, index: int):
        if 0 <= index < len(self.fields) - 1:
            self.fields[index], self.fields[index + 1] = \
                self.fields[index + 1], self.fields[index]

    def update_field(self, index: int, name: str = None, hex_value: str = None,
                     byte_count: int = None, field_type: str = None):
        if 0 <= index < len(self.fields):
            f = self.fields[index]
            if name is not None:
                f.name = name
            if hex_value is not None:
                f.hex_value = hex_value.upper().replace(' ', '')
            if byte_count is not None:
                f.byte_count = byte_count
            if field_type is not None:
                f.field_type = field_type

    def build_packet(self) -> bytes:
        """构建完整数据包，自动计算所有长度字段和校验值"""
        # 找到所有长度字段和所有校验字段
        length_field_indices = []
        checksum_field_indices = []
        for i, f in enumerate(self.fields):
            if f.field_type == FIELD_TYPE_LENGTH:
                length_field_indices.append(i)
            if f.field_type == FIELD_TYPE_CHECKSUM:
                checksum_field_indices.append(i)

        # 第一步: 组装数据（长度和校验字段先填0）
        parts = []
        for f in self.fields:
            if f.field_type in (FIELD_TYPE_CHECKSUM, FIELD_TYPE_LENGTH):
                parts.append(b'\x00' * f.byte_count)
            else:
                parts.append(f.get_bytes())

        # 第二步: 计算每个长度字段（各自独立范围，计算范围内所有字段字节数）
        for li in length_field_indices:
            len_field = self.fields[li]
            total_len = 0
            start = max(0, len_field.length_start)
            end = min(len(self.fields) - 1, len_field.length_end)
            for i in range(start, end + 1):
                total_len += self.fields[i].byte_count
            len_bytes = total_len.to_bytes(
                len_field.byte_count, byteorder=len_field.length_byte_order)
            parts[li] = len_bytes

        # 第三步: 计算每个校验字段的校验值（基于含长度值的数据）
        for chk_idx in checksum_field_indices:
            chk_field = self.fields[chk_idx]
            checksum_data = b''
            start = max(0, chk_field.checksum_start)
            end = min(len(self.fields) - 1, chk_field.checksum_end)
            for i in range(start, end + 1):
                if i != chk_idx:
                    checksum_data += parts[i]

            value, value_bytes = calc_checksum(checksum_data, chk_field.checksum_algorithm)

            if chk_field.checksum_byte_order == 'little':
                value_bytes = value_bytes[::-1]

            if len(value_bytes) < chk_field.byte_count:
                if chk_field.checksum_byte_order == 'big':
                    value_bytes = b'\x00' * (chk_field.byte_count - len(value_bytes)) + value_bytes
                else:
                    value_bytes = value_bytes + b'\x00' * (chk_field.byte_count - len(value_bytes))
            elif len(value_bytes) > chk_field.byte_count:
                value_bytes = value_bytes[-chk_field.byte_count:]

            parts[chk_idx] = value_bytes

        return b''.join(parts)

    def get_preview(self) -> str:
        packet = self.build_packet()
        return bytes_to_hex_str(packet)

    def get_checksum_value_hex(self) -> str:
        packet = self.build_packet()
        for i, f in enumerate(self.fields):
            if f.field_type == FIELD_TYPE_CHECKSUM:
                offset = sum(ff.byte_count for ff in self.fields[:i])
                chk_bytes = packet[offset:offset + f.byte_count]
                return bytes_to_hex_str(chk_bytes)
        return ''

    def to_dict(self) -> dict:
        return {
            'fields': [f.to_dict() for f in self.fields],
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'PacketBuilder':
        pb = cls()
        pb.fields = [PacketField.from_dict(fd) for fd in d['fields']]
        # 兼容旧模板: 全局校验配置迁移到第一个校验字段
        if 'checksum_algorithm' in d and pb.fields:
            for f in pb.fields:
                if f.field_type == FIELD_TYPE_CHECKSUM:
                    f.checksum_algorithm = d.get('checksum_algorithm', 'CRC16/MODBUS')
                    f.checksum_start = d.get('checksum_start', 0)
                    f.checksum_end = d.get('checksum_end', 0)
                    f.checksum_byte_order = d.get('checksum_byte_order', 'big')
                    break
        # 兼容旧模板: 全局长度配置迁移到各长度字段
        if 'length_start' in d:
            g_start = d['length_start']
            g_end = d['length_end']
            g_order = d.get('length_byte_order', 'big')
            for f in pb.fields:
                if f.field_type == FIELD_TYPE_LENGTH:
                    if f.length_start == 0 and f.length_end == 0:
                        f.length_start = g_start
                        f.length_end = g_end
                        f.length_byte_order = g_order
        return pb

    def save_template(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_template(cls, filepath: str) -> 'PacketBuilder':
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))
