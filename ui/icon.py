"""程序图标生成 - 使用 PIL 创建通信信号图标"""

import os
import struct
import zlib


def _create_png_bytes(width: int, height: int, pixels: list) -> bytes:
    """创建 PNG 图片字节"""
    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack('>I', len(data)) + c + crc

    # PNG 签名
    sig = b'\x89PNG\r\n\x1a\n'
    
    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = _chunk(b'IHDR', ihdr_data)
    
    # IDAT - 像素数据 (RGBA)
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter byte
        for x in range(width):
            idx = (y * width + x) * 4
            raw_data += bytes(pixels[idx:idx+4])
    
    compressed = zlib.compress(raw_data)
    idat = _chunk(b'IDAT', compressed)
    
    # IEND
    iend = _chunk(b'IEND', b'')
    
    return sig + ihdr + idat + iend


def get_icon_path() -> str:
    """获取图标文件路径，如果不存在则创建"""
    icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources')
    os.makedirs(icon_dir, exist_ok=True)
    icon_path = os.path.join(icon_dir, 'app_icon.png')
    
    if not os.path.exists(icon_path):
        _generate_icon(icon_path)
    
    return icon_path


def _generate_icon(path: str):
    """生成 32x32 通信信号图标"""
    size = 32
    pixels = []
    
    for y in range(size):
        for x in range(size):
            # 计算到中心的距离
            cx, cy = size // 2, size // 2
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            
            # 信号波纹
            angle = (dx / (dist + 0.01)) if dist > 0 else 0
            
            # 背景透明
            r, g, b, a = 0, 0, 0, 0
            
            # 绘制圆形信号图标
            if dist < 14:  # 内圆
                r, g, b, a = 0, 120, 212, 255  # 蓝色
            elif dist < 15:  # 边框
                r, g, b, a = 0, 150, 255, 255
            elif dist < 16:  # 外边框
                r, g, b, a = 0, 120, 212, 255
            
            # 信号波纹
            if 10 < dist < 11:
                r, g, b, a = 0, 150, 255, 200
            if 12 < dist < 13:
                r, g, b, a = 0, 150, 255, 150
            
            # 中心白色圆点
            if dist < 4:
                r, g, b, a = 255, 255, 255, 255
            
            # 连接线 (从中心到右上)
            if 4 < dist < 12 and dx > 0 and dy < 0 and abs(dx) > abs(dy) * 0.5:
                r, g, b, a = 0, 150, 255, 200
            
            pixels.extend([r, g, b, a])
    
    png_data = _create_png_bytes(size, size, pixels)
    
    with open(path, 'wb') as f:
        f.write(png_data)


if __name__ == '__main__':
    path = get_icon_path()
    print(f'图标已生成: {path}')
