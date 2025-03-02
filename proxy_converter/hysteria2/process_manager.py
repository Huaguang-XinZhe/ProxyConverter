#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hysteria2 进程管理模块
"""

import os
import asyncio
from typing import Dict, Any, Optional

from ..utils.filesystem import find_executable, get_executable_names


class ProcessManager:
    """Hysteria2 进程管理类"""
    
    def __init__(self, executable: str = None):
        """初始化进程管理器
        
        Args:
            executable: Hysteria2 可执行文件路径，不指定则自动查找
        """
        self.executable = executable or self._find_executable()
        self.processes = []
        
        if not self.executable:
            raise FileNotFoundError("找不到 Hysteria2 可执行文件，请确保已安装或指定正确的路径")
    
    async def launch_process(self, config_file: str, config: Dict[str, Any], port: int) -> Dict[str, Any]:
        """启动 Hysteria2 客户端进程
        
        Args:
            config_file: 配置文件路径
            config: 配置内容
            port: HTTP 监听端口
        
        Returns:
            进程信息
        """
        # 构建命令
        cmd = [self.executable, "client", "-c", config_file, "--log-level", "debug"]
        
        print(f"启动 {os.path.basename(config_file)} 的 Hysteria2 客户端...")
        # 从配置中获取 HTTP 监听地址
        http_listen = config.get("http", {}).get("listen", f"127.0.0.1:{port}")
        print(f"HTTP 代理: {http_listen}")
        print(f"服务器: {config.get('server', 'Unknown')}")
        
        try:
            # 使用真正的异步进程创建
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True  # 确保在新的会话中启动
            )
            
            # 创建进程信息
            process_info = {
                "process": process,
                "config_file": config_file,
                "port": port
            }
            
            # 添加到进程列表
            self.processes.append(process_info)
            
            # 返回进程信息
            return process_info
        except Exception as e:
            print(f"启动进程时发生错误: {e}")
            raise
    
    async def check_processes_status(self, future: asyncio.Future) -> None:
        """周期性检查进程状态
        
        Args:
            future: 完成时通知的未来对象
        """
        try:
            while not future.done():
                # 检查进程状态
                for process_info in self.processes[:]:
                    if process_info["process"].returncode is not None:
                        process = process_info["process"]
                        config_file = os.path.basename(process_info['config_file'])
                        print(f"{config_file} 进程已退出，退出码: {process.returncode}")
                        
                        # 尝试读取进程的输出信息
                        try:
                            stdout_data, stderr_data = await asyncio.gather(
                                process.stdout.read(),
                                process.stderr.read()
                            )
                            
                            stdout_str = stdout_data.decode('utf-8', errors='replace').strip()
                            stderr_str = stderr_data.decode('utf-8', errors='replace').strip()
                            
                            if stdout_str:
                                print(f"{config_file} 标准输出:\n{stdout_str}")
                            if stderr_str:
                                print(f"{config_file} 标准错误:\n{stderr_str}")
                        except Exception as e:
                            print(f"无法读取进程输出信息: {e}")
                        
                        self.processes.remove(process_info)
                
                if not self.processes:
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
    
    async def wait_for_interrupt(self) -> None:
        """等待用户中断并清理资源"""
        if not self.processes:
            print("没有运行中的进程")
            return
            
        try:
            print(f"所有连接已建立，按 Ctrl+C 终止...")
            # 创建一个未来对象，它会一直等待，直到被取消
            # 这种方法更优雅地处理中断
            future = asyncio.Future()
            
            # 设置定期检查进程状态的任务
            check_task = asyncio.create_task(self.check_processes_status(future))
            
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
            await self.cleanup_processes()
    
    async def cleanup_processes(self) -> None:
        """清理所有进程"""
        if not self.processes:
            return
            
        # 并发终止所有进程
        cleanup_tasks = []
        for process_info in self.processes:
            cleanup_tasks.append(self._cleanup_single_process(process_info))
        
        # 等待所有清理任务完成，但设置超时
        try:
            await asyncio.wait_for(asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=3.0)
        except asyncio.TimeoutError:
            print("清理进程超时，某些进程可能未正常终止")
            
        # 清空进程列表
        self.processes = []
            
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
