#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理转换工具主程序
"""

import argparse
import asyncio
import os
import random
import re

from proxy_converter.proxy_converter import ProxyConverter
from proxy_converter.hysteria2.client import Hysteria2Client


def find_config_files_by_ports(config_dir: str, ports: list) -> list:
    """根据端口列表查找对应的配置文件
    
    Args:
        config_dir: 配置文件目录
        ports: 端口列表
        
    Returns:
        匹配的配置文件名列表
    """
    if not os.path.exists(config_dir):
        print(f"配置目录 {config_dir} 不存在")
        return []
    
    # 获取目录中所有配置文件
    config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
    
    # 匹配端口号的正则表达式
    port_pattern = re.compile(r'-(\d+)\.json$')
    
    # 存储匹配的配置文件
    matched_files = []
    
    # 遍历所有配置文件，检查文件名中的端口号是否在端口列表中
    for file in config_files:
        match = port_pattern.search(file)
        if match:
            file_port = int(match.group(1))
            if file_port in ports:
                matched_files.append(os.path.basename(file))
    
    return matched_files


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="代理配置转换工具")
    
    # 基本参数
    parser.add_argument("--yaml-file", "-Y", 
                        default="C:\\Users\\24750\\AppData\\Roaming\\io.github.clash-verge-rev.clash-verge-rev\\profiles\\RNxaxXM4uPWP.yaml", 
                        help="YAML 配置文件路径")
    parser.add_argument("--type", "-T", default="hysteria2", help="代理类型，默认为 hysteria2")
    parser.add_argument("--output-dir", "-O", default="./configs", help="配置文件输出目录，默认为 ./configs")
    parser.add_argument("--count", "-C", type=int, default=5, help="随机选择的代理数量，默认为 5")
    parser.add_argument("--executable", "-E", help="Hysteria2 可执行文件路径")
    parser.add_argument("--filter", "-F", help="配置文件过滤模式，支持正则表达式或以 | 分隔的多个文件名")
    
    args = parser.parse_args()
    
    # 步骤 1：转换代理配置
    print("步骤 1: 正在转换代理配置...")
    converter = ProxyConverter(args.yaml_file)
    config_files = await converter.generate_all_configs(args.type, args.output_dir)
    if not config_files:
        print("未能生成有效的代理配置文件，程序退出")
        return
    
    # 如果指定了过滤模式，则直接使用过滤模式连接
    if args.filter:
        print(f"使用指定的过滤模式: {args.filter}")
        
        # 创建 Hysteria2 客户端
        client = Hysteria2Client(config_dir=args.output_dir, executable=args.executable)
        
        try:
            # 批量连接代理
            print("\n正在建立连接...")
            await client.batch_connect(filter_pattern=args.filter)
            
            # 等待用户中断
            await client.wait_for_interrupt()
        except Exception as e:
            print(f"连接代理时出错: {e}")
        finally:
            # 清理资源
            await client.cleanup()
        
        return
    
    # 步骤 2：从保存的端口范围文件中读取端口信息
    print("步骤 2: 正在读取端口范围...")
    ports_file = "proxy_ports.txt"
    
    if not os.path.exists(ports_file):
        print(f"端口范围文件 {ports_file} 不存在，程序退出")
        return
    
    try:
        with open(ports_file, 'r', encoding='utf-8') as f:
            port_range = f.read().strip()
            start_port, end_port = map(int, port_range.split('-'))
            available_ports = list(range(start_port, end_port + 1))
    except Exception as e:
        print(f"读取端口范围文件时出错: {e}")
        return
    
    if not available_ports:
        print("可用端口列表为空，程序退出")
        return
    
    # 步骤 3：随机选择指定数量的端口
    print(f"步骤 3: 正在随机选择 {args.count} 个端口...")
    
    # 如果要选择的数量大于可用端口数量，则使用所有端口
    if args.count >= len(available_ports):
        selected_ports = available_ports
    else:
        # 随机选择端口
        selected_ports = random.sample(available_ports, args.count)
    
    if not selected_ports:
        print("未能选择到有效端口，程序退出")
        return
    
    # 打印选择的端口
    print("\n随机选择的代理地址:")
    for port in selected_ports:
        print(f"127.0.0.1:{port}")
    
    # 步骤 4：建立连接
    print("\n步骤 4: 正在建立连接...")
    
    # 创建 Hysteria2 客户端
    client = Hysteria2Client(config_dir=args.output_dir, executable=args.executable)
    
    try:
        # 根据选择的端口查找对应的配置文件
        selected_config_files = find_config_files_by_ports(args.output_dir, selected_ports)
        
        if not selected_config_files:
            print("未找到对应的配置文件，程序退出")
            return
        
        # 批量连接代理，使用精确匹配模式
        # 将文件名列表转换为 | 分隔的字符串，用于精确匹配
        filter_pattern = "|".join(selected_config_files)
        print(f"使用过滤器: {filter_pattern}")
        await client.batch_connect(filter_pattern=filter_pattern)
        
        # 等待用户中断
        await client.wait_for_interrupt()
    except Exception as e:
        print(f"连接代理时出错: {e}")
    finally:
        # 清理资源
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
