#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理转换工具主程序
"""

import argparse
import asyncio
import os

from proxy_converter.proxy_converter import ProxyConverter
from proxy_converter.hysteria2.client import Hysteria2Client
from proxy_converter.api_server import ProxyAPIServer


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="代理配置转换工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 转换命令
    convert_parser = subparsers.add_parser("convert", help="转换代理配置")
    convert_parser.add_argument("--yaml-file", "-Y", default='./config.yaml', help="YAML 配置文件路径") # 不带两个中划线的就是必须的参数！
    convert_parser.add_argument("--type", "-T", default="hysteria2", help="代理类型，默认为 hysteria2")
    convert_parser.add_argument("--output-dir", "-O", default="./configs", help="配置文件输出目录，默认为 ./configs")
    
    # 连接命令
    connect_parser = subparsers.add_parser("connect", help="连接代理")
    connect_parser.add_argument("-C", "--config", default='./configs/1hk.json', help="单个配置文件路径")
    connect_parser.add_argument("-D", "--config-dir", default='./configs', help="配置文件目录，用于批量连接")
    connect_parser.add_argument("-E", "--executable", help="Hysteria2 可执行文件路径")
    connect_parser.add_argument("-B", "--batch", action="store_true", help="批量连接模式")
    connect_parser.add_argument("-L", "--limit", type=int, default=0, help="限制批量连接的配置文件数量，0 表示不限制")
    connect_parser.add_argument("-F", "--filter", type=str, help="过滤配置文件的模式")
    connect_parser.add_argument("-M", "--max-parallel", type=int, default=0, help="最大并发连接数，0 表示不限制")
    connect_parser.add_argument("-H", "--host", default="127.0.0.1", help="API 服务监听主机")
    connect_parser.add_argument("-P", "--port", type=int, default=8000, help="API 服务监听端口")
    
    # API 服务命令
    api_parser = subparsers.add_parser("api", help="启动 API 服务")
    api_parser.add_argument("-D", "--config-dir", default='./configs', help="配置文件目录")
    api_parser.add_argument("-H", "--host", default="127.0.0.1", help="监听主机")
    api_parser.add_argument("-P", "--port", type=int, default=8000, help="监听端口")
    
    args = parser.parse_args()
    
    if args.command == "convert":
        # 转换命令
        converter = ProxyConverter(args.yaml_file)
        await converter.generate_all_configs(args.type, args.output_dir)
    elif args.command == "connect":
        # 连接命令
        client = None
        
        if args.batch:
            # 批量连接模式
            client = Hysteria2Client(config_dir=args.config_dir, executable=args.executable)
            await client.batch_connect(
                limit=args.limit, 
                filter_pattern=args.filter,
                max_parallel=args.max_parallel
            )
            
            
            print(f"正在启动 API 服务...")
            # 创建 API 服务器但不等待
            api_task = asyncio.create_task(
                start_api_server(args.config_dir, args.host, args.port)
            )
            
            try:
                await asyncio.sleep(0.1) # 让 API 的日志先打印
                # 等待用户中断
                await client.wait_for_interrupt()
            finally:
                # 取消 API 任务
                if not api_task.done():
                    api_task.cancel()
                    try:
                        await api_task
                    except asyncio.CancelledError:
                        pass
        else:
            # 单个连接模式 - 使用批量连接方法，但只指定一个配置文件名
            # 创建一个临时的 select 列表，只包含指定的配置文件名
            config_filename = os.path.basename(args.config)
            
            # 使用批量连接方法，但只选择一个配置文件
            client = Hysteria2Client(config_dir=os.path.dirname(args.config), executable=args.executable)
            await client.batch_connect(
                limit=1,
                filter_pattern=config_filename
            )
            
            # 等待用户中断
            await client.wait_for_interrupt()
    elif args.command == "api":
        # 启动 API 服务
        await start_api_server(args.config_dir, args.host, args.port)
    else:
        parser.print_help()


async def start_api_server(config_dir, host, port):
    """启动 API 服务器

    Args:
        config_dir: 配置文件目录
        host: 监听主机
        port: 监听端口
    """
    api_server = ProxyAPIServer(
        config_dir=config_dir,
        host=host,
        port=port
    )
    print(f"正在启动 API 服务，监听地址: http://{host}:{port}")
    await api_server.start()


if __name__ == "__main__":
    asyncio.run(main())
