#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通用配置管理模块
"""

import os
import json
import socket
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
            filter_pattern: 过滤模式(文件名匹配),None 表示不过滤
        
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
            filtered_files = [file for file in all_files 
                            if filter_pattern.lower() in os.path.basename(file).lower()]
            all_files = filtered_files
            
        if not all_files:
            return []
            
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
