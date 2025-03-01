#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hysteria2 客户端模块，用于管理 Hysteria2 代理连接
"""

import os
import json
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from .utils.network import is_port_in_use
from .utils.filesystem import find_executable, create_temp_config_file, get_executable_names, list_config_files


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
        self.executable = executable or self._find_executable()
        self.process = None
        
        if not self.executable:
            raise FileNotFoundError("找不到 Hysteria2 可执行文件，请确保已安装或指定正确的路径")
        
        if self.config_dir and not self._validate_config_dir():
            raise ValueError(f"无效的配置目录: {self.config_dir}")
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
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

    async def batch_connect(
        self, 
        limit: int = 0, 
        filter_pattern: str = None,
        max_parallel: int = 0
    ) -> List[Dict[str, Any]]:
        """批量连接多个服务器

        Args:
            local_http_port_start: 本地 HTTP 代理起始端口（该参数保留但不再使用，使用配置文件中的端口）
            limit: 最大连接数量，0 表示不限制
            filter_pattern: 过滤配置文件的模式，None 表示不过滤
            max_parallel: 最大并发数，0 表示不限制

        Returns:
            连接结果列表
        """
        # 获取所有配置文件
        config_files = []
        if self.config_dir and os.path.isdir(self.config_dir):
            config_files = self._select_config_files(limit, filter_pattern)
        else:
            print(f"配置目录 {self.config_dir} 不存在或不是目录")
            return []
        
        if not config_files:
            return []
        
        # 批量连接结果和进程列表
        results = []
        processes = []
        
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
                
            result_data, process_info = result
            results.append(result_data)
            if result_data["success"] and process_info:
                processes.append(process_info)
        
        # 统计连接结果
        successful_count = sum(1 for result in results if result["success"])
        print(f"成功连接 {successful_count}/{len(results)} 个服务器")
        
        total_end_time = time.time()
        print(f"整个批量连接过程完成，总耗时: {total_end_time - total_start_time:.2f}秒")
        
        # 等待用户中断
        if processes:
            await self._wait_for_interrupt(processes)
        else:
            print("没有成功连接的进程，程序结束")
        
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
                config = self.load_config(config_file)
                
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

    async def _connect_one(self, resource: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """连接单个服务器 - 真正的异步实现

        Args:
            resource: 包含连接所需资源的字典

        Returns:
            (连接结果, 进程信息)
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
            }, None
        
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
            }, None
        
        try:
            # 启动进程 - 使用异步方式
            process_info = await self._launch_process_async(config_file, config, port)
            
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
                }, None
            
            # 连接成功
            end_time = time.time()
            print(f"[{config_name}] 连接成功。HTTP 代理: {http_listen}。耗时: {end_time - start_time:.2f}秒")
            
            return {
                "config_file": config_file,
                "success": True,
                "port": port,
                "http_listen": http_listen,
                "process_info": {
                    "process": process_info["process"],
                    "config_file": config_file
                }
            }, process_info
            
        except Exception as e:
            end_time = time.time()
            print(f"[{config_name}] 连接出错: {e}。耗时: {end_time - start_time:.2f}秒")
                
            return {
                "config_file": config_file,
                "success": False,
                "port": port,
                "error": str(e)
            }, None

    async def _launch_process_async(self, config_file: str, config: Dict[str, Any], port: int) -> Dict[str, Any]:
        """以异步方式启动 Hysteria2 客户端进程

        Args:
            config_file: 配置文件路径
            config: 配置内容
            port: HTTP 监听端口

        Returns:
            进程信息
        """
        # 构建命令
        cmd = [self.executable, "client", "-c", config_file]
        
        print(f"启动 {os.path.basename(config_file)} 的 Hysteria2 客户端...")
        # 从配置中获取 HTTP 监听地址
        http_listen = config.get("http", {}).get("listen", f"127.0.0.1:{port}")
        print(f"HTTP 代理: {http_listen}")
        print(f"服务器: {config.get('server', 'Unknown')}")
        
        # 使用真正的异步进程创建
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True  # 确保在新的会话中启动
        )
        
        # 返回进程信息
        return {
            "process": process,
            "config_file": config_file,
            "port": port
        }

    def _validate_config_dir(self) -> bool:
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

    def _select_config_files(self, limit: int = 0, filter_pattern: str = None) -> List[str]:
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
        
    def _select_specific_config(self, filename: str) -> List[str]:
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

    async def _wait_for_interrupt(self, processes: List[Dict[str, Any]]) -> None:
        """等待用户中断并清理资源

        Args:
            processes: 进程信息列表
        """
        try:
            print(f"所有连接已建立，按 Ctrl+C 终止...")
            # 创建一个未来对象，它会一直等待，直到被取消
            # 这种方法更优雅地处理中断
            future = asyncio.Future()
            
            # 设置定期检查进程状态的任务
            check_task = asyncio.create_task(self._check_processes_status(processes, future))
            
            try:
                # 等待未来对象，它只会在键盘中断时被取消
                await future
            except asyncio.CancelledError:
                # 显式处理 CancelledError，避免它传播
                pass
            finally:
                # 确保检查任务被取消
                check_task.cancel()
                
        except KeyboardInterrupt:
            print("正在停止所有连接...")
        except Exception as e:
            print(f"等待过程中发生错误: {e}")
        finally:
            # 清理所有资源
            await self._cleanup_processes(processes)
    
    async def _check_processes_status(self, processes: List[Dict[str, Any]], future: asyncio.Future) -> None:
        """周期性检查进程状态
        
        Args:
            processes: 进程信息列表
            future: 完成时通知的未来对象
        """
        try:
            while not future.done():
                # 检查进程状态
                for process_info in processes[:]:
                    if process_info["process"].returncode is not None:
                        print(f"{os.path.basename(process_info['config_file'])} 进程已退出，退出码: {process_info['process'].returncode}")
                        processes.remove(process_info)
                
                if not processes:
                    print("所有进程已退出，程序结束")
                    # 设置未来对象为完成状态，通知主循环退出
                    future.set_result(None)
                    break
                
                # 短暂等待后再次检查
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            # 显式处理取消，避免错误传播
            pass
        except Exception as e:
            print(f"检查进程状态时出错: {e}")
            
    async def _cleanup_processes(self, processes: List[Dict[str, Any]]) -> None:
        """清理所有进程和临时文件

        Args:
            processes: 进程信息列表
        """
        if not processes:
            return
            
        # 并发终止所有进程
        cleanup_tasks = []
        for process_info in processes:
            cleanup_tasks.append(self._cleanup_single_process(process_info))
        
        # 等待所有清理任务完成，但设置超时
        try:
            await asyncio.wait_for(asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=3.0)
        except asyncio.TimeoutError:
            print("清理进程超时，某些进程可能未正常终止")
            
        print("已清理所有资源")
    
    async def _cleanup_single_process(self, process_info: Dict[str, Any]) -> None:
        """清理单个进程
        
        Args:
            process_info: 进程信息
        """
        try:
            process = process_info["process"]
            
            # 终止进程
            if process.returncode is None:
                print(f"正在终止进程: {os.path.basename(process_info.get('config_file', 'unknown'))}")
                # 使用系统特定的方法终止进程
                if hasattr(process, "terminate"):
                    process.terminate()
                    # 等待一小段时间让进程自行终止
                    try:
                        await asyncio.wait_for(process.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # 如果进程没有及时终止，强制杀死它
                        if hasattr(process, "kill"):
                            process.kill()
                elif hasattr(process, "kill"):
                    process.kill()
                else:
                    # 兜底方法
                    try:
                        os.kill(process.pid, 9)
                    except:
                        pass
                print(f"进程已终止: {os.path.basename(process_info.get('config_file', 'unknown'))}")
        except Exception as e:
            print(f"清理进程 {process_info.get('config_file', 'unknown')} 时出错: {e}")

    def _find_executable(self) -> Optional[str]:
        """查找 Hysteria2 可执行文件

        Returns:
            可执行文件路径，未找到则返回 None
        """
        return find_executable(get_executable_names("hysteria"))
