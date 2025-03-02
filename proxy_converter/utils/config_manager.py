#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通用配置管理模块
"""

import os
import json
import re
from typing import List, Dict, Any, Optional

from .filesystem import list_config_files


class ConfigManager:
    """通用配置管理类"""
    
    def __init__(self, config_dir: str = None):
        """初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir
        
    def validate_config_dir(self) -> bool:
        """验证配置目录是否有效
        
        Returns:
            是否有效
        """
        if not self.config_dir:
            return False
            
        if not os.path.exists(self.config_dir):
            return False
            
        if not os.path.isdir(self.config_dir):
            return False
            
        # 检查是否有配置文件
        config_files = list_config_files(self.config_dir)
        if not config_files:
            return False
            
        return True
    
    def select_config_files(self, limit: int = 0, filter_pattern: str = None) -> List[str]:
        """选择配置文件
        
        Args:
            limit: 最大文件数量，0 表示不限制
            filter_pattern: 过滤模式，支持以下格式：
                            1. 单个文件名：直接匹配文件名
                            2. 多个文件名：使用 | 分隔的多个文件名，精确匹配任意一个
                            3. 正则表达式：匹配文件名的正则表达式
        
        Returns:
            配置文件路径列表
        """
        if not self.config_dir or not os.path.isdir(self.config_dir):
            return []
            
        all_files = list_config_files(self.config_dir)
        if not all_files:
            return []
            
        # 应用过滤
        if filter_pattern:
            # 检查是否是使用 | 分隔的多个文件名
            if "|" in filter_pattern:
                # 分割成多个文件名，并创建精确匹配的列表
                file_patterns = filter_pattern.split("|")
                filtered_files = []
                for file in all_files:
                    file_name = os.path.basename(file)
                    if file_name in file_patterns:
                        filtered_files.append(file)
                all_files = filtered_files
            else:
                # 尝试作为正则表达式处理
                try:
                    pattern = re.compile(filter_pattern, re.IGNORECASE)
                    filtered_files = []
                    for file in all_files:
                        file_name = os.path.basename(file)
                        if pattern.search(file_name):
                            filtered_files.append(file)
                    all_files = filtered_files
                except re.error:
                    # 如果不是有效的正则表达式，则当作普通字符串处理
                    filtered_files = [file for file in all_files 
                                    if filter_pattern.lower() in os.path.basename(file).lower()]
                    all_files = filtered_files
            
        # 应用限制
        if limit > 0 and len(all_files) > limit:
            all_files = all_files[:limit]
            
        # 排序
        all_files.sort()
            
        return all_files
        
    def select_specific_config(self, filename: str) -> List[str]:
        """选择特定的配置文件
        
        Args:
            filename: 配置文件名（带后缀）
        
        Returns:
            配置文件路径列表
        """
        if not self.config_dir or not os.path.isdir(self.config_dir):
            return []
            
        all_files = list_config_files(self.config_dir)
        if not all_files:
            return []
            
        selected_files = []
        for file in all_files:
            if os.path.basename(file) == filename:
                selected_files.append(file)
        return selected_files
    
    @staticmethod
    def load_config(config_file: str) -> Dict[str, Any]:
        """加载配置文件
        
        Args:
            config_file: 配置文件路径
        
        Returns:
            配置字典
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"配置文件 {config_file} 不是有效的 JSON 文件")
        except Exception as e:
            raise Exception(f"加载配置文件 {config_file} 时出错: {e}")
