#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hysteria2 客户端模块，用于管理 Hysteria2 代理连接
"""

from typing import List, Dict, Any

from ..utils.config_manager import ConfigManager
from .process_manager import ProcessManager
from .connection import ConnectionManager


class Hysteria2Client:
    """Hysteria2 客户端封装类，用于建立 Hysteria2 代理连接"""

    def __init__(self, config_file: str = None, config_dir: str = None, executable: str = None):
        """初始化 Hysteria2 客户端

        Args:
            config_file: 配置文件路径
            config_dir: 配置文件目录，当需要批量连接时使用
            executable: Hysteria2 可执行文件路径，不指定则自动查找
        """
        self.config_file = config_file
        self.config_dir = config_dir
        
        # 初始化各个管理器
        self.config_manager = ConfigManager(config_dir)
        self.process_manager = ProcessManager(executable)
        self.connection_manager = ConnectionManager(self.config_manager, self.process_manager)
        
        # 验证配置目录
        if self.config_dir and not self.config_manager.validate_config_dir():
            raise ValueError(f"无效的配置目录: {self.config_dir}")
    
    async def batch_connect(
        self, 
        limit: int = 0, 
        filter_pattern: str = None,
        max_parallel: int = 0
    ) -> List[Dict[str, Any]]:
        """批量连接多个服务器

        Args:
            limit: 最大连接数量，0 表示不限制
            filter_pattern: 过滤配置文件的模式，None 表示不过滤
            max_parallel: 最大并发数，0 表示不限制

        Returns:
            连接结果列表
        """
        # 使用连接管理器进行批量连接
        return await self.connection_manager.connect_batch(
            limit=limit,
            filter_pattern=filter_pattern,
            max_parallel=max_parallel
        )
    
    async def wait_for_interrupt(self):
        """等待用户中断并清理资源"""
        await self.process_manager.wait_for_interrupt()
    
    async def cleanup(self):
        """清理所有资源"""
        await self.process_manager.cleanup_processes()
