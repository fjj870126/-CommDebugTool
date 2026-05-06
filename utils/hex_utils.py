"""Hex/ASCII 转换工具函数"""


def hex_str_to_bytes(hex_str: str) -> bytes:
    """将hex字符串转为bytes, 如 'AA 55 01' -> b'\xaa\x55\x01'"""
    hex_str = hex_str.replace(' ', '').replace('\n', '').replace('\r', '')
    if len(hex_str) % 2 != 0:
        hex_str = '0' + hex_str
    return bytes.fromhex(hex_str)


def bytes_to_hex_str(data: bytes, separator: str = ' ') -> str:
    """将bytes转为hex字符串, 如 b'\xaa\x55' -> 'AA 55'"""
    return separator.join(f'{b:02X}' for b in data)


def bytes_to_ascii_str(data: bytes) -> str:
    """将bytes转为可显示的ASCII字符串, 不可打印字符用.替代"""
    return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)


def bytes_to_hex_ascii(data: bytes) -> str:
    """混合显示: Hex + ASCII"""
    hex_part = bytes_to_hex_str(data)
    ascii_part = bytes_to_ascii_str(data)
    return f'{hex_part}  |  {ascii_part}'


def format_hex_input(s: str) -> str:
    """格式化 HEX 输入：去除非HEX字符，每两位加空格，转大写"""
    # 移除所有非HEX字符
    clean = ''.join(c for c in s if c.isalnum())
    clean = ''.join(c for c in clean if c.upper() in '0123456789ABCDEF')
    # 每两位加空格
    result = ' '.join(clean[i:i+2] for i in range(0, len(clean), 2))
    return result.upper()

def hex_to_all(data: bytes) -> dict:
    """将 HEX 数据转为 ASCII / Decimal / Binary 预览"""
    if not data:
        return {}
    return {
        'hex': bytes_to_hex_str(data),
        'ascii': bytes_to_ascii_str(data),
        'decimal': ' '.join(str(b) for b in data),
        'binary': ' '.join(f'{b:08b}' for b in data),
        'len': len(data),
    }

def is_valid_hex(s: str) -> bool:
    """检查字符串是否为合法的hex值"""
    s = s.replace(' ', '')
    if not s:
        return False
    try:
        int(s, 16)
        return len(s) % 2 == 0
    except ValueError:
        return False
