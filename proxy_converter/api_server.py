#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API 服务模块，提供 HTTP API 端点获取代理地址
"""

import os
import json
import asyncio
import socket
from typing import List, Dict, Any, Optional
from aiohttp import web
import aiofiles
from .utils.config_manager import ConfigManager


class ProxyAPIServer:
    """代理 API 服务器，提供 HTTP API 端点获取代理地址"""

    def __init__(self, config_dir: str = "./configs", host: str = "127.0.0.1", port: int = 8000):
        """初始化 API 服务器

        Args:
            config_dir: 配置文件目录
            host: 监听主机
            port: 监听端口
        """
        self.config_dir = config_dir
        self.host = host
        self.port = port
        self.app = web.Application()
        self.config_manager = ConfigManager(config_dir)
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/api/proxies", self.handle_get_proxies)
        self.app.router.add_get("/api/proxy", self.handle_get_proxy)

    async def handle_index(self, request):
        """处理首页请求

        Args:
            request: 请求对象

        Returns:
            响应对象
        """
        try:
            with open(os.path.join(os.path.dirname(__file__), "templates", "index.html"), "r", encoding="utf-8") as f:
                html_content = f.read()
            return web.Response(text=html_content, content_type="text/html")
        except Exception as e:
            return web.Response(text=f"加载首页模板失败: {e}", content_type="text/plain", status=500)

    async def handle_get_proxies(self, request):
        """处理获取代理列表请求

        Args:
            request: 请求对象

        Returns:
            响应对象
        """
        # 获取查询参数
        limit = int(request.query.get("limit", "0"))
        filter_pattern = request.query.get("filter")
        check_availability = request.query.get("check") == "1"
        format_type = request.query.get("format", "text")

        # 获取代理列表
        proxies = await self._get_http_proxies(
            limit=limit,
            filter_pattern=filter_pattern,
            check_availability=check_availability
        )

        if not proxies:
            if format_type.lower() == "json":
                return web.json_response({"error": "未找到符合条件的代理"}, status=404)
            else:
                return web.Response(text="未找到符合条件的代理", content_type="text/plain", status=404)

        # 根据格式返回
        if format_type.lower() == "json":
            # JSON 格式
            return web.json_response(proxies)
        else:
            # 纯文本格式，每行一个代理地址
            text_content = "\n".join([f"{proxy['host']}:{proxy['port']}" for proxy in proxies])
            return web.Response(text=text_content, content_type="text/plain")

    async def handle_get_proxy(self, request):
        """处理获取单个代理请求

        Args:
            request: 请求对象

        Returns:
            响应对象
        """
        # 获取查询参数
        random_select = request.query.get("random") == "1"
        format_type = request.query.get("format", "text")

        # 获取所有代理
        proxies = await self._get_http_proxies()
        
        if not proxies:
            return web.Response(text="未找到可用代理", status=404, content_type="text/plain")

        # 选择代理
        if random_select:
            import random
            proxy = random.choice(proxies)
        else:
            # 默认选择第一个
            proxy = proxies[0]

        # 根据格式返回
        if format_type.lower() == "json":
            return web.json_response(proxy)
        else:
            # 纯文本格式，只返回代理地址
            return web.Response(text=f"{proxy['host']}:{proxy['port']}", content_type="text/plain")

    async def start(self):
        """启动 API 服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"API 服务器已启动，监听地址: http://{self.host}:{self.port}")
        
        # 保持运行
        try:
            # 创建一个未来对象，它会一直等待，直到被取消
            future = asyncio.Future()
            
            try:
                # 等待未来对象，它只会在键盘中断时被取消
                await future
            except asyncio.CancelledError:
                # 显式处理 CancelledError，避免它传播
                print("API 服务器正在关闭...")
        except KeyboardInterrupt:
            print("收到键盘中断，API 服务器正在关闭...")
        finally:
            # 关闭服务器
            await runner.cleanup()
            print("API 服务器已关闭")
    
    async def _get_http_proxies(
        self, 
        limit: int = 0, 
        filter_pattern: str = None,
        check_availability: bool = False
    ) -> List[Dict[str, Any]]:
        """获取 HTTP 代理地址列表

        Args:
            limit: 最大返回数量，0 表示不限制
            filter_pattern: 过滤配置文件的模式，None 表示不过滤
            check_availability: 是否检查代理可用性

        Returns:
            代理地址列表，每个元素包含 name, url, host, port 等信息
        """
        # 获取所有配置文件
        config_files = self.config_manager.select_config_files(limit, filter_pattern)
        if not config_files:
            return []

        # 并发获取代理信息
        tasks = [self._get_proxy_from_config(config_file) for config_file in config_files]
        proxies = await asyncio.gather(*tasks)
        
        # 过滤无效代理
        valid_proxies = [proxy for proxy in proxies if proxy is not None]
        
        # 检查可用性
        if check_availability:
            availability_tasks = [self._check_proxy_availability(proxy) for proxy in valid_proxies]
            availability_results = await asyncio.gather(*availability_tasks)
            
            # 更新可用性信息
            for i, available in enumerate(availability_results):
                valid_proxies[i]["available"] = available
        
        return valid_proxies

    async def _get_proxy_from_config(self, config_file: str) -> Optional[Dict[str, Any]]:
        """从配置文件中获取代理信息

        Args:
            config_file: 配置文件路径

        Returns:
            代理信息，包含 name, url, host, port 等
        """
        try:
            # 使用异步文件操作
            async with aiofiles.open(config_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                config = json.loads(content)
            
            # 检查必要的字段
            if "http" not in config or "listen" not in config["http"]:
                return None
            
            http_listen = config["http"]["listen"]
            # 解析监听地址
            try:
                host, port_str = http_listen.rsplit(":", 1)
                port = int(port_str)
            except (ValueError, TypeError):
                return None
            
            # 构建代理信息
            proxy_info = {
                "name": config.get("name", os.path.basename(config_file)),
                "url": f"http://{http_listen}",
                "host": host,
                "port": port,
                "config_file": config_file,
                "server": config.get("server", "未知服务器")
            }
            
            return proxy_info
        except Exception as e:
            print(f"解析配置文件 {os.path.basename(config_file)} 时出错: {e}")
            return None

    async def _check_proxy_availability(self, proxy: Dict[str, Any]) -> bool:
        """检查代理是否可用

        Args:
            proxy: 代理信息

        Returns:
            代理是否可用
        """
        host = proxy.get("host", "127.0.0.1")
        port = proxy.get("port", 0)
        
        if not port:
            return False
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)  # 设置超时时间
                result = s.connect_ex((host, port))
                return result == 0
        except Exception:
            return False