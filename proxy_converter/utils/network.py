#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络工具模块，包含网络相关的通用功能
"""

import socket

# 这也是个耗时过程！
def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用

    Args:
        port: 要检查的端口

    Returns:
        端口是否被占用
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


async def find_available_port(start_port: int = 8080) -> int:
    """查找可用端口

    Args:
        start_port: 起始端口号

    Returns:
        可用的端口号
    """
    port = start_port
    while is_port_in_use(port):
        port += 1
        # 避免无限循环，设置上限
        if port > start_port + 1000:
            print(f"警告：无法在 {start_port} 到 {start_port + 1000} 范围内找到可用端口")
            return 0
    return port
