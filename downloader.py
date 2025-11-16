#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频下载器 V2.0
支持用户主页视频批量下载
"""

import re
import os
import sys
import time
import json
import argparse
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import print as rprint
import yaml

console = Console()


class DownloadStats:
    """下载统计"""
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()

    def add_success(self):
        self.success += 1

    def add_failed(self):
        self.failed += 1

    def add_skipped(self):
        self.skipped += 1

    def get_success_rate(self):
        if self.total == 0:
            return 0
        return (self.success / self.total) * 100

    def get_elapsed_time(self):
        return time.time() - self.start_time

    def print_summary(self):
        table = Table(title="下载统计")
        table.add_column("项目", style="cyan")
        table.add_column("数量", style="magenta")

        table.add_row("总计", str(self.total))
        table.add_row("成功", str(self.success))
        table.add_row("失败", str(self.failed))
        table.add_row("跳过", str(self.skipped))
        table.add_row("成功率", f"{self.get_success_rate():.2f}%")
        table.add_row("耗时", f"{self.get_elapsed_time():.2f}秒")

        console.print(table)


class RateLimiter:
    """请求限流器"""
    def __init__(self, max_requests_per_second=2):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0

    def wait_if_needed(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_interval:
            time.sleep(self.min_interval - time_since_last_request)
        self.last_request_time = time.time()


class DouyinDownloader:
    """抖音下载器主类"""

    @staticmethod
    def show_cookie_help():
        """显示如何获取Cookie的帮助信息"""
        console.print("\n[bold yellow]如何获取抖音Cookie：[/bold yellow]")
        console.print("1. 在浏览器中打开 https://www.douyin.com 并登录")
        console.print("2. 按 F12 打开开发者工具")
        console.print("3. 切换到 'Network' (网络) 标签")
        console.print("4. 刷新页面（F5）")
        console.print("5. 在请求列表中点击任意请求")
        console.print("6. 在右侧找到 'Request Headers' (请求标头)")
        console.print("7. 找到 'Cookie' 字段，复制整个值")
        console.print("8. 将Cookie值填入 config.yml 或使用 --cookie 参数\n")

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stats = DownloadStats()
        self.rate_limiter = RateLimiter(max_requests_per_second=2)
        self.session = requests.Session()

        # 设置请求头
        # 注意：不要手动设置Accept-Encoding，让requests自动处理gzip解压
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        # 设置Cookie
        if self.config.get('cookie'):
            self.headers['Cookie'] = self.config['cookie']
            console.print(f"[green]✓ 已设置Cookie，长度: {len(self.config['cookie'])}[/green]")
        else:
            console.print(f"[bold red]✗ 警告：未设置Cookie！[/bold red]")
            console.print(f"[yellow]抖音需要登录状态才能获取用户视频列表[/yellow]")
            self.show_cookie_help()

        self.session.headers.update(self.headers)

        # 创建下载目录
        self.download_path = Path(config.get('path', './Downloaded'))
        self.download_path.mkdir(parents=True, exist_ok=True)

    def extract_user_id(self, url: str) -> Optional[str]:
        """从URL中提取用户ID"""
        # 匹配 /user/ 后面的用户ID（包含字母、数字、下划线、连字符）
        patterns = [
            r'/user/([\w-]+)',  # 修复：包含连字符
            r'sec_uid=([\w-]+)',  # 修复：包含连字符
            r'MS4wLjABAAAA[\w-]+',  # sec_uid格式
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                user_id = match.group(1) if '(' in pattern else match.group(0)
                console.print(f"[cyan]提取的用户ID: {user_id}[/cyan]")
                return user_id

        return None

    def get_real_url(self, short_url: str) -> str:
        """解析短链接获取真实URL"""
        try:
            self.rate_limiter.wait_if_needed()
            response = self.session.head(short_url, allow_redirects=True, timeout=10)
            return response.url
        except Exception as e:
            console.print(f"[yellow]解析短链接失败: {e}，使用原URL[/yellow]")
            return short_url

    def get_single_video_info(self, aweme_id: str) -> Optional[Dict]:
        """获取单个视频的最新信息（用于刷新过期的下载链接）"""
        try:
            # 使用备用API获取单个视频信息
            api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/"
            params = {
                'item_ids': aweme_id
            }

            self.rate_limiter.wait_if_needed()
            response = self.session.get(api_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if 'item_list' in data and len(data['item_list']) > 0:
                    return data['item_list'][0]

            return None

        except Exception as e:
            console.print(f"[yellow]获取单个视频信息失败: {e}[/yellow]")
            return None

    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        try:
            # 使用抖音Web API获取用户信息
            api_url = f"https://www.douyin.com/aweme/v1/web/aweme/post/"
            params = {
                'sec_user_id': user_id,
                'count': 10,
                'max_cursor': 0,
            }

            self.rate_limiter.wait_if_needed()
            response = self.session.get(api_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                console.print(f"[red]获取用户信息失败，状态码: {response.status_code}[/red]")
                return None

        except Exception as e:
            console.print(f"[red]获取用户信息异常: {e}[/red]")
            return None

    def get_user_videos(self, user_id: str, max_count: int = 0) -> List[Dict]:
        """获取用户的所有视频列表"""
        videos = []
        max_cursor = 0
        has_more = True
        page = 1

        console.print(f"[cyan]正在获取用户视频列表...[/cyan]")

        while has_more:
            try:
                # 抖音用户作品API
                api_url = "https://www.douyin.com/aweme/v1/web/aweme/post/"
                params = {
                    'device_platform': 'webapp',
                    'aid': '6383',
                    'channel': 'channel_pc_web',
                    'sec_user_id': user_id,
                    'max_cursor': max_cursor,
                    'locate_query': 'false',
                    'show_live_replay_strategy': '1',
                    'count': '18',
                    'publish_video_strategy_type': '2',
                    'pc_client_type': '1',
                    'version_code': '170400',
                    'version_name': '17.4.0',
                }

                self.rate_limiter.wait_if_needed()
                response = self.session.get(api_url, params=params, timeout=15)

                if page <= 2:  # 只在前两页显示详细调试信息
                    console.print(f"[cyan]API请求URL: {response.url[:100]}...[/cyan]")
                    console.print(f"[cyan]响应状态码: {response.status_code}[/cyan]")
                    console.print(f"[cyan]Content-Encoding: {response.headers.get('content-encoding', 'none')}[/cyan]")
                    console.print(f"[cyan]Content-Type: {response.headers.get('content-type')}[/cyan]")
                    console.print(f"[cyan]响应内容长度: {len(response.content)} bytes[/cyan]")

                if response.status_code != 200:
                    console.print(f"[red]API请求失败，状态码: {response.status_code}[/red]")
                    console.print(f"[yellow]响应内容: {response.text[:500]}[/yellow]")
                    break

                # 检查响应内容是否为空
                if not response.content or len(response.content) == 0:
                    console.print(f"[yellow]第{page}页响应为空，可能已到达最后一页[/yellow]")
                    break

                # 尝试解析JSON
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    console.print(f"[red]JSON解析失败: {e}[/red]")

                    # 检查是否是gzip压缩但未解压的问题
                    content_encoding = response.headers.get('content-encoding', '')
                    if content_encoding or response.content[:2] == b'\x1f\x8b':  # gzip magic number
                        console.print(f"[yellow]检测到压缩数据，尝试手动解压...[/yellow]")
                        try:
                            import gzip
                            decompressed = gzip.decompress(response.content)
                            data = json.loads(decompressed.decode('utf-8'))
                            console.print(f"[green]手动解压成功！[/green]")
                        except Exception as decompress_error:
                            console.print(f"[red]手动解压也失败: {decompress_error}[/red]")
                            console.print(f"[yellow]响应内容前100字节(hex): {response.content[:100].hex()}[/yellow]")
                            if page == 1:
                                break
                            else:
                                console.print(f"[cyan]已获取{page-1}页，可能已到达最后一页[/cyan]")
                                break
                    else:
                        console.print(f"[yellow]响应内容前500字符: {response.text[:500]}[/yellow]")
                        console.print(f"[yellow]响应内容类型: {response.headers.get('content-type')}[/yellow]")
                        # 如果是第一页就失败，退出；否则可能是已到末尾
                        if page == 1:
                            break
                        else:
                            console.print(f"[cyan]已获取{page-1}页，可能已到达最后一页[/cyan]")
                            break

                # 打印响应数据的键，用于调试
                console.print(f"[cyan]响应数据包含的键: {list(data.keys())}[/cyan]")

                # 检查响应数据
                if 'aweme_list' not in data:
                    console.print(f"[bold red]✗ 未找到视频列表！[/bold red]")

                    # 检查是否是登录问题
                    if data.get('status_code') != 0:
                        console.print(f"[yellow]API错误码: {data.get('status_code')}[/yellow]")
                        console.print(f"[yellow]错误信息: {data.get('status_msg', '未知错误')}[/yellow]")

                    if not self.config.get('cookie'):
                        console.print(f"[yellow]原因：未设置Cookie，抖音需要登录才能访问用户视频[/yellow]")
                        self.show_cookie_help()
                    else:
                        console.print(f"[yellow]可能原因：Cookie已过期或无效，请重新获取[/yellow]")

                    console.print(f"\n[dim]API响应: {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}[/dim]")
                    break

                aweme_list = data.get('aweme_list', [])

                if not aweme_list:
                    console.print(f"[yellow]第{page}页没有更多视频[/yellow]")
                    break

                videos.extend(aweme_list)
                console.print(f"[green]已获取第{page}页，共{len(aweme_list)}个视频，累计{len(videos)}个[/green]")

                # 检查是否还有更多
                has_more = data.get('has_more', False)
                max_cursor = data.get('max_cursor', 0)

                # 检查是否达到最大数量
                if max_count > 0 and len(videos) >= max_count:
                    videos = videos[:max_count]
                    console.print(f"[cyan]已达到设定的最大数量 {max_count}[/cyan]")
                    break

                page += 1
                # 增加延迟，避免请求过快被限流
                time.sleep(1.0)  # 从0.5秒增加到1秒

            except Exception as e:
                console.print(f"[red]获取视频列表异常: {e}[/red]")
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")

                # 如果是第一页就失败，退出；否则继续
                if page == 1:
                    console.print(f"[red]第一页获取失败，无法继续[/red]")
                    break
                else:
                    console.print(f"[yellow]已成功获取{page-1}页，继续返回已获取的视频[/yellow]")
                    break

        console.print(f"[green]共获取到 {len(videos)} 个视频[/green]")
        return videos

    def get_video_download_url(self, aweme_info: Dict) -> Optional[str]:
        """从视频信息中提取无水印下载地址"""
        try:
            video_data = aweme_info.get('video', {})

            # 优先使用play_addr
            play_addr = video_data.get('play_addr', {})
            if play_addr and 'url_list' in play_addr:
                url = play_addr['url_list'][0]
                # 替换为无水印链接
                url = url.replace('playwm', 'play')
                # 尝试获取更高清晰度
                url = url.replace('720p', '1080p')
                return url

            # 备选：download_addr
            download_addr = video_data.get('download_addr', {})
            if download_addr and 'url_list' in download_addr:
                return download_addr['url_list'][0]

            return None

        except Exception as e:
            console.print(f"[red]提取下载地址失败: {e}[/red]")
            return None

    def sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # 移除或替换非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')

        # 限制文件名长度
        if len(filename) > 200:
            filename = filename[:200]

        return filename.strip()

    def download_video(self, video_url: str, save_path: Path, video_info: Dict, max_retries: int = 3) -> bool:
        """下载单个视频（带重试机制）"""
        # 检查文件是否已存在
        if save_path.exists():
            console.print(f"[yellow]文件已存在，跳过: {save_path.name}[/yellow]")
            self.stats.add_skipped()
            return True

        # 重试循环
        for retry in range(max_retries):
            try:
                if retry > 0:
                    wait_time = retry * 2  # 递增等待时间：2秒、4秒
                    console.print(f"[yellow]等待{wait_time}秒后重试... (第{retry+1}/{max_retries}次)[/yellow]")
                    time.sleep(wait_time)

                # 下载视频
                self.rate_limiter.wait_if_needed()

                # 为视频下载添加Referer，避免403
                headers = {
                    'Referer': 'https://www.douyin.com/',
                    'User-Agent': self.headers['User-Agent']
                }

                response = self.session.get(video_url, stream=True, timeout=60, headers=headers)
                response.raise_for_status()

                # 获取文件大小
                total_size = int(response.headers.get('content-length', 0))

                # 保存视频
                temp_path = save_path.with_suffix('.tmp')  # 使用临时文件
                with open(temp_path, 'wb') as f:
                    if total_size == 0:
                        f.write(response.content)
                    else:
                        downloaded = 0
                        chunk_size = 1024 * 1024  # 1MB chunks，更大的块提高速度
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                # 下载完成，重命名临时文件
                temp_path.rename(save_path)

                # 保存视频信息
                info_path = save_path.with_suffix('.json')
                with open(info_path, 'w', encoding='utf-8') as f:
                    json.dump(video_info, f, ensure_ascii=False, indent=2)

                console.print(f"[green]✓ 下载成功: {save_path.name}[/green]")
                self.stats.add_success()
                return True

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    console.print(f"[yellow]⚠ 403错误，视频链接可能已过期: {save_path.name}[/yellow]")
                    if retry < max_retries - 1:
                        console.print(f"[cyan]尝试刷新下载链接...[/cyan]")

                        # 从video_info中获取aweme_id
                        aweme_id = video_info.get('aweme_id')
                        if aweme_id:
                            # 重新获取该视频的最新信息
                            fresh_info = self.get_single_video_info(aweme_id)
                            if fresh_info:
                                # 从新信息中获取下载链接
                                fresh_url = self.get_video_download_url(fresh_info)
                                if fresh_url and fresh_url != video_url:
                                    console.print(f"[green]✓ 成功刷新下载链接[/green]")
                                    video_url = fresh_url  # 更新为新链接
                                    video_info = fresh_info  # 更新视频信息
                                    continue  # 使用新链接重试

                        console.print(f"[yellow]无法刷新链接，使用原链接重试[/yellow]")
                        continue
                    else:
                        console.print(f"[red]✗ 下载失败（403）: {save_path.name}[/red]")
                else:
                    console.print(f"[red]HTTP错误 {e.response.status_code}: {save_path.name}[/red]")
                    if retry < max_retries - 1:
                        continue

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ChunkedEncodingError) as e:
                console.print(f"[yellow]⚠ 网络错误: {type(e).__name__} - {save_path.name}[/yellow]")
                if retry < max_retries - 1:
                    continue
                else:
                    console.print(f"[red]✗ 下载失败（网络错误）: {save_path.name}[/red]")

            except Exception as e:
                console.print(f"[red]✗ 下载失败: {save_path.name} - {e}[/red]")
                if retry < max_retries - 1:
                    continue

            finally:
                # 清理临时文件
                temp_path = save_path.with_suffix('.tmp')
                if temp_path.exists():
                    temp_path.unlink()

        # 所有重试都失败
        self.stats.add_failed()
        return False

    def download_user_videos(self, url: str):
        """下载用户主页的所有视频"""
        console.print(f"[bold cyan]开始处理用户主页: {url}[/bold cyan]")

        # 解析短链接
        if 'v.douyin.com' in url or 'iesdouyin.com' in url:
            console.print("[cyan]检测到短链接，正在解析...[/cyan]")
            url = self.get_real_url(url)
            console.print(f"[cyan]解析后的URL: {url}[/cyan]")

        # 提取用户ID
        user_id = self.extract_user_id(url)
        if not user_id:
            console.print("[red]无法从URL中提取用户ID[/red]")
            return

        console.print(f"[cyan]用户ID: {user_id}[/cyan]")

        # 创建用户专属文件夹
        user_folder = self.download_path / self.sanitize_filename(user_id)
        user_folder.mkdir(parents=True, exist_ok=True)

        # 获取视频列表
        max_count = self.config.get('max_count', 0)
        videos = self.get_user_videos(user_id, max_count)

        if not videos:
            console.print("[yellow]未获取到任何视频[/yellow]")
            return

        # 反转视频列表：从最老的视频开始下载（默认API返回的是从新到旧）
        oldest_first = self.config.get('oldest_first', True)  # 默认从最老开始
        if oldest_first:
            videos.reverse()
            console.print(f"[cyan]已反转视频顺序，将从最老的视频开始下载[/cyan]")
        else:
            console.print(f"[cyan]保持原始顺序，将从最新的视频开始下载[/cyan]")

        self.stats.total = len(videos)

        # 下载视频
        console.print(f"\n[bold green]开始下载 {len(videos)} 个视频...[/bold green]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]下载进度...", total=len(videos))

            for idx, video in enumerate(videos, 1):
                try:
                    # 获取视频信息
                    aweme_id = video.get('aweme_id', '')
                    desc = video.get('desc', '无标题')
                    author = video.get('author', {}).get('nickname', '未知作者')

                    # 构建文件名
                    filename = f"{idx}_{aweme_id}_{self.sanitize_filename(desc[:50])}.mp4"
                    save_path = user_folder / filename

                    # 获取下载地址
                    download_url = self.get_video_download_url(video)
                    if not download_url:
                        console.print(f"[yellow]第{idx}个视频无法获取下载地址，跳过[/yellow]")
                        self.stats.add_failed()
                        progress.update(task, advance=1)
                        continue

                    # 下载视频
                    progress.update(task, description=f"[cyan]下载中: {filename[:50]}...")
                    self.download_video(download_url, save_path, video)

                    progress.update(task, advance=1)

                except Exception as e:
                    console.print(f"[red]处理第{idx}个视频时出错: {e}[/red]")
                    self.stats.add_failed()
                    progress.update(task, advance=1)
                    continue

        # 打印统计信息
        console.print(f"\n[bold green]下载完成！[/bold green]")
        console.print(f"[cyan]保存路径: {user_folder}[/cyan]\n")
        self.stats.print_summary()


def load_config(config_path: Optional[str] = None) -> Dict:
    """加载配置文件"""
    if config_path and Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    # 默认配置
    return {
        'path': './Downloaded',
        'max_count': 0,  # 0表示不限制
        'cookie': '',
        'oldest_first': True,  # 默认从最老的视频开始下载
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='抖音视频下载器 V2.2')
    parser.add_argument('-u', '--url', type=str, help='用户主页链接')
    parser.add_argument('-c', '--config', type=str, help='配置文件路径')
    parser.add_argument('-p', '--path', type=str, help='下载保存路径')
    parser.add_argument('--cookie', type=str, help='抖音Cookie')
    parser.add_argument('--max-count', type=int, help='最大下载数量（0为不限制）')

    # 视频下载顺序选项
    order_group = parser.add_mutually_exclusive_group()
    order_group.add_argument('--oldest-first', action='store_true',
                            help='从最老的视频开始下载（默认）')
    order_group.add_argument('--newest-first', action='store_true',
                            help='从最新的视频开始下载')

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 命令行参数覆盖配置文件
    if args.path:
        config['path'] = args.path
    if args.cookie:
        config['cookie'] = args.cookie
    if args.max_count is not None:
        config['max_count'] = args.max_count

    # 处理视频下载顺序
    if args.oldest_first:
        config['oldest_first'] = True
    elif args.newest_first:
        config['oldest_first'] = False

    # 获取URL
    url = args.url
    if not url and config.get('url'):
        url = config['url']

    if not url:
        console.print("[red]错误: 请提供用户主页链接[/red]")
        console.print("使用方法: python downloader.py -u <用户主页链接>")
        console.print("示例: python downloader.py -u https://www.douyin.com/user/MS4wLjABAAAA...")
        sys.exit(1)

    # 创建下载器并开始下载
    try:
        downloader = DouyinDownloader(config)
        downloader.download_user_videos(url)
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断下载[/yellow]")
    except Exception as e:
        console.print(f"[red]程序异常: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
