"""手写CRC校验算法实现 - CRC8/CRC16/CRC32全系列
不依赖任何第三方CRC库，全部基于查表法实现。
"""


def _reflect(value: int, width: int) -> int:
    """位反转: 将value的低width位进行镜像反转"""
    result = 0
    for i in range(width):
        if value & (1 << i):
            result |= 1 << (width - 1 - i)
    return result


def _build_table(poly: int, width: int) -> list:
    """构建CRC查找表"""
    table = []
    top_bit = 1 << (width - 1)
    mask = (1 << width) - 1
    for i in range(256):
        crc = i << (width - 8)
        for _ in range(8):
            if crc & top_bit:
                crc = ((crc << 1) ^ poly) & mask
            else:
                crc = (crc << 1) & mask
        table.append(crc)
    return table


def _crc_calc(data: bytes, width: int, poly: int, init: int,
              ref_in: bool, ref_out: bool, xor_out: int) -> int:
    """通用CRC计算引擎"""
    mask = (1 << width) - 1
    table = _build_table(poly, width)
    crc = init & mask

    for byte in data:
        if ref_in:
            byte = _reflect(byte, 8)
        idx = ((crc >> (width - 8)) ^ byte) & 0xFF
        crc = ((crc << 8) ^ table[idx]) & mask

    if ref_out:
        crc = _reflect(crc, width)

    return (crc ^ xor_out) & mask


# ============================================================
# CRC8 算法族
# ============================================================

CRC8_ALGORITHMS = {
    'CRC8': {
        'poly': 0x07, 'init': 0x00,
        'ref_in': False, 'ref_out': False, 'xor_out': 0x00,
        'desc': 'CRC-8 标准',
    },
    'CRC8/ITU': {
        'poly': 0x07, 'init': 0x00,
        'ref_in': False, 'ref_out': False, 'xor_out': 0x55,
        'desc': 'CRC-8/ITU',
    },
    'CRC8/ROHC': {
        'poly': 0x07, 'init': 0xFF,
        'ref_in': True, 'ref_out': True, 'xor_out': 0x00,
        'desc': 'CRC-8/ROHC',
    },
    'CRC8/MAXIM': {
        'poly': 0x31, 'init': 0x00,
        'ref_in': True, 'ref_out': True, 'xor_out': 0x00,
        'desc': 'CRC-8/MAXIM (Dallas/1-Wire)',
    },
}


def crc8(data: bytes, algorithm: str = 'CRC8') -> int:
    """计算CRC8"""
    cfg = CRC8_ALGORITHMS[algorithm]
    return _crc_calc(data, 8, cfg['poly'], cfg['init'],
                     cfg['ref_in'], cfg['ref_out'], cfg['xor_out'])


# ============================================================
# CRC16 算法族
# ============================================================

CRC16_ALGORITHMS = {
    'CRC16/MODBUS': {
        'poly': 0x8005, 'init': 0xFFFF,
        'ref_in': True, 'ref_out': True, 'xor_out': 0x0000,
        'desc': 'CRC-16/MODBUS',
    },
    'CRC16/IBM': {
        'poly': 0x8005, 'init': 0x0000,
        'ref_in': True, 'ref_out': True, 'xor_out': 0x0000,
        'desc': 'CRC-16/IBM (ARC)',
    },
    'CRC16/CCITT': {
        'poly': 0x1021, 'init': 0x0000,
        'ref_in': True, 'ref_out': True, 'xor_out': 0x0000,
        'desc': 'CRC-16/CCITT (Kermit)',
    },
    'CRC16/CCITT-FALSE': {
        'poly': 0x1021, 'init': 0xFFFF,
        'ref_in': False, 'ref_out': False, 'xor_out': 0x0000,
        'desc': 'CRC-16/CCITT-FALSE',
    },
    'CRC16/XMODEM': {
        'poly': 0x1021, 'init': 0x0000,
        'ref_in': False, 'ref_out': False, 'xor_out': 0x0000,
        'desc': 'CRC-16/XMODEM',
    },
    'CRC16/X25': {
        'poly': 0x1021, 'init': 0xFFFF,
        'ref_in': True, 'ref_out': True, 'xor_out': 0xFFFF,
        'desc': 'CRC-16/X25',
    },
    'CRC16/USB': {
        'poly': 0x8005, 'init': 0xFFFF,
        'ref_in': True, 'ref_out': True, 'xor_out': 0xFFFF,
        'desc': 'CRC-16/USB',
    },
    'CRC16/DNP': {
        'poly': 0x3D65, 'init': 0x0000,
        'ref_in': True, 'ref_out': True, 'xor_out': 0xFFFF,
        'desc': 'CRC-16/DNP',
    },
}


def crc16(data: bytes, algorithm: str = 'CRC16/MODBUS') -> int:
    """计算CRC16"""
    cfg = CRC16_ALGORITHMS[algorithm]
    return _crc_calc(data, 16, cfg['poly'], cfg['init'],
                     cfg['ref_in'], cfg['ref_out'], cfg['xor_out'])


# ============================================================
# CRC32 算法族
# ============================================================

CRC32_ALGORITHMS = {
    'CRC32': {
        'poly': 0x04C11DB7, 'init': 0xFFFFFFFF,
        'ref_in': True, 'ref_out': True, 'xor_out': 0xFFFFFFFF,
        'desc': 'CRC-32 标准',
    },
    'CRC32/MPEG2': {
        'poly': 0x04C11DB7, 'init': 0xFFFFFFFF,
        'ref_in': False, 'ref_out': False, 'xor_out': 0x00000000,
        'desc': 'CRC-32/MPEG-2',
    },
    'CRC32/POSIX': {
        'poly': 0x04C11DB7, 'init': 0x00000000,
        'ref_in': False, 'ref_out': False, 'xor_out': 0xFFFFFFFF,
        'desc': 'CRC-32/POSIX (cksum)',
    },
}


def crc32(data: bytes, algorithm: str = 'CRC32') -> int:
    """计算CRC32"""
    cfg = CRC32_ALGORITHMS[algorithm]
    return _crc_calc(data, 32, cfg['poly'], cfg['init'],
                     cfg['ref_in'], cfg['ref_out'], cfg['xor_out'])


# ============================================================
# 累加和 / 异或校验
# ============================================================

def checksum_sum8(data: bytes) -> int:
    """单字节累加和校验 (取低8位)"""
    return sum(data) & 0xFF


def checksum_sum16(data: bytes) -> int:
    """双字节累加和校验 (取低16位)"""
    return sum(data) & 0xFFFF


def checksum_xor8(data: bytes) -> int:
    """单字节异或校验"""
    result = 0
    for b in data:
        result ^= b
    return result


# ============================================================
# 统一调用接口
# ============================================================

ALL_ALGORITHMS = {}

def _make_crc8_func(name):
    return lambda d: crc8(d, name)

def _make_crc16_func(name):
    return lambda d: crc16(d, name)

def _make_crc32_func(name):
    return lambda d: crc32(d, name)

for name, cfg in CRC8_ALGORITHMS.items():
    ALL_ALGORITHMS[name] = {
        'func': _make_crc8_func(name),
        'width': 1,  # 结果字节数
        'desc': cfg['desc'],
        'group': 'CRC8',
    }

for name, cfg in CRC16_ALGORITHMS.items():
    ALL_ALGORITHMS[name] = {
        'func': _make_crc16_func(name),
        'width': 2,
        'desc': cfg['desc'],
        'group': 'CRC16',
    }

for name, cfg in CRC32_ALGORITHMS.items():
    ALL_ALGORITHMS[name] = {
        'func': _make_crc32_func(name),
        'width': 4,
        'desc': cfg['desc'],
        'group': 'CRC32',
    }

ALL_ALGORITHMS['SUM8'] = {
    'func': checksum_sum8, 'width': 1,
    'desc': '累加和(8位)', 'group': '累加和',
}
ALL_ALGORITHMS['SUM16'] = {
    'func': checksum_sum16, 'width': 2,
    'desc': '累加和(16位)', 'group': '累加和',
}
ALL_ALGORITHMS['XOR8'] = {
    'func': checksum_xor8, 'width': 1,
    'desc': '异或校验(8位)', 'group': '异或',
}


def calc_checksum(data: bytes, algorithm: str) -> tuple:
    """计算校验值
    返回: (校验值int, 校验值bytes)
    """
    alg = ALL_ALGORITHMS[algorithm]
    value = alg['func'](data)
    width = alg['width']
    result_bytes = value.to_bytes(width, byteorder='big')
    return value, result_bytes


def get_algorithm_names() -> list:
    """获取所有算法名称列表"""
    return list(ALL_ALGORITHMS.keys())


def get_algorithm_width(algorithm: str) -> int:
    """获取算法结果的字节宽度"""
    return ALL_ALGORITHMS[algorithm]['width']
