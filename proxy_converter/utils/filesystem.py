#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件系统工具模块，包含文件操作相关的通用功能
"""

import os
import shutil
import platform
import tempfile
import json
from typing import Optional, Dict, Any, List


def find_executable(executable_names: List[str]) -> Optional[str]:
    """查找可执行文件

    Args:
        executable_names: 可执行文件名列表

    Returns:
        可执行文件路径，未找到则返回 None
    """
    # 首先检查当前目录
    for name in executable_names:
        path = os.path.join(os.getcwd(), name)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    # 然后检查 PATH
    for name in executable_names:
        path = shutil.which(name)
        if path:
            return path
    
    return None


def create_temp_config_file(config: Dict[str, Any], prefix: str = 'temp_') -> str:
    """创建临时配置文件

    Args:
        config: 配置字典
        prefix: 临时文件前缀

    Returns:
        临时文件路径
    """
    # 使用不含特殊字符的临时文件名（文件关闭后不会自动删除）
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json', prefix=prefix)
    
    try:
        with open(temp_file.name, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return temp_file.name
    except Exception as e:
        print(f"创建临时配置文件时出错: {e}")
        try:
            os.unlink(temp_file.name)
        except:
            pass
        return None


def get_executable_names(base_name: str) -> List[str]:
    """根据操作系统获取可执行文件名列表

    Args:
        base_name: 基本文件名

    Returns:
        可执行文件名列表
    """
    if platform.system() == "Windows":
        return [f"{base_name}.exe", base_name]
    else:
        return [base_name, f"{base_name}.exe"]


def list_config_files(directory: str, extension: str = '.json') -> List[str]:
    """列出目录中的配置文件

    Args:
        directory: 目录路径
        extension: 文件扩展名

    Returns:
        配置文件路径列表
    """
    if not os.path.isdir(directory):
        print(f"错误：目录不存在: {directory}")
        return []
    
    config_files = []
    for file in os.listdir(directory):
        if file.endswith(extension):
            config_files.append(os.path.join(directory, file))
    
    return config_files
