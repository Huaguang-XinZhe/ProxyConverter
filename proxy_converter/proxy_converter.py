#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理转换器模块，用于从 YAML 文件中提取代理信息并转换为各种代理客户端的配置
"""

import yaml
import os
import sys
import json
import asyncio
from typing import Dict, Any, List

from .utils.network import is_port_in_use


class ProxyConverter:
    """代理转换器，用于从 YAML 文件中提取代理信息并建立连接"""

    def __init__(self, yaml_file: str):
        """初始化代理转换器

        Args:
            yaml_file: YAML 文件路径
        """
        self.yaml_file = yaml_file
        self.proxies = []
        self.load_yaml()

    def load_yaml(self) -> None:
        """加载 YAML 文件并提取代理信息"""
        try:
            with open(self.yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if 'proxies' in config:
                    self.proxies = config['proxies']
                    print(f"成功加载 {len(self.proxies)} 个代理配置")
                else:
                    print("错误：YAML 文件中未找到 'proxies' 部分")
        except Exception as e:
            print(f"加载 YAML 文件时出错: {e}")
            sys.exit(1)

    def get_proxy_by_type(self, proxy_type: str = None) -> List[Dict[str, Any]]:
        """按类型获取代理列表

        Args:
            proxy_type: 代理类型，如 'hysteria2'，不指定则返回所有代理

        Returns:
            符合条件的代理列表
        """
        if proxy_type:
            return [p for p in self.proxies if p.get('type') == proxy_type]
        return self.proxies

    async def generate_hysteria2_config(self, proxy: Dict[str, Any], output_dir: str = "./configs", port: int = 8080) -> str:
        """生成 Hysteria2 配置文件

        Args:
            proxy: 代理配置
            output_dir: 输出目录
            port: 预分配的端口号

        Returns:
            配置文件路径
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 取 server 名的前部分作为文件名
        server_prefix = proxy.get('server', 'unknown').split('.')[0]
        filename = f"{server_prefix}.json"
        filepath = os.path.join(output_dir, filename)
        
        # 获取节点名称，优先使用配置中的 name
        name = proxy.get('name', server_prefix)
        
        # 直接使用传入的预分配端口
        
        # 创建配置
        config = {
            "server": proxy.get('server'),
            "auth": proxy.get('password'),
            "tls": {
                "insecure": proxy.get('skip-cert-verify', False)
            },
            "transport": {},
            # 添加 HTTP 监听配置，使用预分配的端口
            "http": {"listen": f"127.0.0.1:{port}"},
            # 添加节点名称
            "name": name
        }
        
        # 处理端口
        if 'port' in proxy:
            config["server"] += f":{proxy['port']}"
        elif 'ports' in proxy:
            # 如果有端口范围，使用第一个端口
            ports = proxy['ports'].split('-')
            if len(ports) == 2:
                config["server"] += f":{ports[0]}"  
        
        # 写入文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"配置已保存到: {filepath}，HTTP 监听地址: 127.0.0.1:{port}")
            return filepath
        except Exception as e:
            print(f"保存配置文件时出错: {e}")
            return None

    async def generate_all_configs(self, proxy_type: str = 'hysteria2', output_dir: str = "./configs") -> List[str]:
        """生成所有代理的配置文件，使用预分配的端口实现真正并发

        Args:
            proxy_type: 代理类型
            output_dir: 输出目录

        Returns:
            配置文件路径列表
        """
        proxies = self.get_proxy_by_type(proxy_type)
        if not proxies:
            print(f"未找到类型为 {proxy_type} 的代理")
            return []
        
        print(f"正在为 {len(proxies)} 个 {proxy_type} 代理生成配置文件...")
        
        # 预分配端口，起始端口为 8080
        start_port = 8080
        ports = [start_port + i for i in range(len(proxies))]
        
        # 使用并发方式生成配置文件，传入预分配的端口
        tasks = []
        for i, proxy in enumerate(proxies):
            if proxy_type == 'hysteria2':
                tasks.append(self.generate_hysteria2_config(proxy, output_dir, ports[i]))
        
        # 并发执行所有任务
        config_files = await asyncio.gather(*tasks)
        # 过滤掉 None 值
        config_files = [f for f in config_files if f]
        
        print(f"已生成 {len(config_files)} 个配置文件")
        return config_files
