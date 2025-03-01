#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hysteria2 连接管理模块
"""

import os
import time
import asyncio
from typing import List, Dict, Any

from ..utils.config_manager import ConfigManager
from .process_manager import ProcessManager


class ConnectionManager:
    """Hysteria2 连接管理类"""
    
    def __init__(self, config_manager: ConfigManager, process_manager: ProcessManager):
        """初始化连接管理器
        
        Args:
            config_manager: 配置管理器
            process_manager: 进程管理器
        """
        self.config_manager = config_manager
        self.process_manager = process_manager
    
    async def connect_batch(
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
        # 获取所有配置文件
        config_files = []
        if self.config_manager.config_dir and os.path.isdir(self.config_manager.config_dir):
            config_files = self.config_manager.select_config_files(limit, filter_pattern)
        else:
            print(f"配置目录 {self.config_manager.config_dir} 不存在或不是目录")
            return []
        
        if not config_files:
            return []
        
        # 批量连接结果
        results = []
        
        # 控制并发数
        semaphore = asyncio.Semaphore(max_parallel if max_parallel > 0 else len(config_files))
        
        print(f"准备并发连接 {len(config_files)} 个服务器...")
        total_start_time = time.time()
        
        # 预分配资源
        resources = await self._prepare_resources(config_files)
        
        # 创建并发任务，使用真正的异步方式
        async def connect_with_semaphore(resource):
            async with semaphore:
                return await self._connect_one(resource)
        
        # 创建所有任务
        connection_tasks = [connect_with_semaphore(resource) for resource in resources]
        
        print(f"开始并发执行 {len(connection_tasks)} 个连接任务...")
        connection_start_time = time.time()
        
        # 并发执行所有连接任务
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        connection_end_time = time.time()
        print(f"连接阶段完成，耗时: {connection_end_time - connection_start_time:.2f}秒")
        
        # 处理连接结果
        for result in connection_results:
            if isinstance(result, Exception):
                # 处理异常情况
                print(f"连接任务发生异常: {result}")
                continue
                
            results.append(result)
        
        # 统计连接结果
        successful_count = sum(1 for result in results if result["success"])
        print(f"成功连接 {successful_count}/{len(results)} 个服务器")
        
        total_end_time = time.time()
        print(f"整个批量连接过程完成，总耗时: {total_end_time - total_start_time:.2f}秒")
        
        return results
    
    async def _prepare_resources(self, config_files: List[str]) -> List[Dict[str, Any]]:
        """预先准备所有连接所需的资源
        
        Args:
            config_files: 配置文件列表
            
        Returns:
            资源列表，每个资源包含配置文件和配置内容
        """
        resources = []
        
        resource_prepare_start = time.time()
        # 并发准备资源
        async def prepare_one_resource(config_file):
            # 加载配置
            try:
                config = self.config_manager.load_config(config_file)
                
                # 检查配置是否包含 HTTP 监听配置
                if "http" not in config or "listen" not in config["http"]:
                    print(f"配置文件 {os.path.basename(config_file)} 不包含 HTTP 监听配置，跳过")
                    return None
                
                return {
                    "config_file": config_file,
                    "config": config
                }
            except Exception as e:
                print(f"准备资源失败 {os.path.basename(config_file)}: {e}")
                return None
        
        # 并发准备所有资源
        resource_tasks = [prepare_one_resource(config_file) for config_file in config_files]
        
        resource_results = await asyncio.gather(*resource_tasks)
        
        # 过滤无效资源
        resources = [r for r in resource_results if r is not None]
        
        resource_prepare_end = time.time()
        print(f"资源准备完成，耗时: {resource_prepare_end - resource_prepare_start:.2f}秒")
        
        return resources
    
    async def _connect_one(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """连接单个服务器
        
        Args:
            resource: 包含连接所需资源的字典
        
        Returns:
            连接结果
        """
        config_file = resource["config_file"]
        config = resource["config"]
        
        start_time = time.time()
        config_name = os.path.basename(config_file)
        
        # 获取监听端口
        http_listen = config.get("http", {}).get("listen", "")
        if not http_listen:
            end_time = time.time()
            print(f"[{config_name}] 配置中没有 HTTP 监听地址，无法连接。耗时: {end_time - start_time:.2f}秒")
            return {
                "config_file": config_file,
                "success": False,
                "error": "配置中没有 HTTP 监听地址"
            }
        
        # 提取端口
        try:
            port = int(http_listen.split(":")[-1])
        except:
            end_time = time.time()
            print(f"[{config_name}] 无法解析 HTTP 监听地址 {http_listen}。耗时: {end_time - start_time:.2f}秒")
            return {
                "config_file": config_file,
                "success": False,
                "error": f"无法解析 HTTP 监听地址 {http_listen}"
            }
        
        try:
            # 启动进程
            process_info = await self.process_manager.launch_process(config_file, config, port)
            
            # 仅等待很短时间检查进程是否立即失败
            await asyncio.sleep(0.2)
            
            # 检查进程是否正常运行
            returncode = process_info["process"].returncode
            if returncode is not None:
                end_time = time.time()
                print(f"[{config_name}] 进程已退出，退出码: {returncode}。耗时: {end_time - start_time:.2f}秒")
                    
                return {
                    "config_file": config_file,
                    "success": False,
                    "port": port,
                    "error": f"进程立即退出，退出码: {returncode}"
                }
            
            # 连接成功
            end_time = time.time()
            print(f"[{config_name}] 连接成功。HTTP 代理: {http_listen}。耗时: {end_time - start_time:.2f}秒")
            
            return {
                "config_file": config_file,
                "success": True,
                "port": port,
                "http_listen": http_listen
            }
            
        except Exception as e:
            end_time = time.time()
            print(f"[{config_name}] 连接出错: {e}。耗时: {end_time - start_time:.2f}秒")
                
            return {
                "config_file": config_file,
                "success": False,
                "port": port,
                "error": str(e)
            }
