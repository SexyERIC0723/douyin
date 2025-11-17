#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频下载 + YouTube 上传集成脚本
边下载边上传，上传后删除本地文件，节省空间
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
from rich import print as rprint
import yaml

# YouTube API
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

console = Console()

# ================== YouTube 配置 ==================

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "token.json"
UPLOADED_LOG = BASE_DIR / "uploaded_videos.json"

DEFAULT_PRIVACY_STATUS = "public"
DEFAULT_CATEGORY_ID = "22"  # People & Blogs


# ================== 下载器核心类 ==================

class DownloadStats:
    """下载统计"""
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.uploaded = 0
        self.start_time = time.time()

    def add_success(self):
        self.success += 1

    def add_failed(self):
        self.failed += 1

    def add_uploaded(self):
        self.uploaded += 1

    def get_elapsed_time(self):
        return time.time() - self.start_time


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


class DouyinYouTubeUploader:
    """抖音下载 + YouTube 上传集成类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stats = DownloadStats()
        self.rate_limiter = RateLimiter(max_requests_per_second=2)
        self.session = requests.Session()

        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.douyin.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        if self.config.get('cookie'):
            self.headers['Cookie'] = self.config['cookie']
            console.print(f"[green]✓ 已设置Cookie[/green]")
        else:
            console.print(f"[bold red]✗ 未设置Cookie！[/bold red]")

        self.session.headers.update(self.headers)

        # 创建临时下载目录
        self.temp_download_path = Path(config.get('temp_path', './temp_download'))
        self.temp_download_path.mkdir(parents=True, exist_ok=True)

        # 初始化 YouTube 服务
        self.youtube = self.get_youtube_service()

        # 加载已上传记录
        self.uploaded_ids = self.load_uploaded_ids()

    # ================== YouTube 相关方法 ==================

    def get_youtube_service(self):
        """获取 YouTube 服务"""
        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), YOUTUBE_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                console.print("[cyan]🔄 刷新 Google 授权...[/cyan]")
                creds.refresh(Request())
            else:
                console.print("[yellow]🧾 需要在浏览器完成 Google 授权[/yellow]")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRET_FILE),
                    YOUTUBE_SCOPES
                )
                creds = flow.run_local_server(port=0)
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

        return build("youtube", "v3", credentials=creds)

    def load_uploaded_ids(self):
        """加载已上传的 aweme_id 集合"""
        if not UPLOADED_LOG.exists():
            return set()
        try:
            data = json.loads(UPLOADED_LOG.read_text(encoding="utf-8"))
            return set(str(x) for x in data)
        except Exception:
            return set()

    def save_uploaded_ids(self):
        """保存已上传的 aweme_id 集合"""
        UPLOADED_LOG.write_text(
            json.dumps(sorted(list(self.uploaded_ids)), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def upload_to_youtube(self, video_path: Path, video_info: Dict) -> Optional[str]:
        """上传视频到 YouTube"""
        try:
            # 准备标题和描述
            desc = video_info.get('desc', '').strip()
            title = desc[:100] if desc else "抖音视频"
            description = desc

            console.print(f"[cyan]🚀 开始上传到 YouTube: {title[:50]}...[/cyan]")

            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": DEFAULT_CATEGORY_ID,
                },
                "status": {
                    "privacyStatus": DEFAULT_PRIVACY_STATUS,
                    "selfDeclaredMadeForKids": True,
                },
            }

            media = MediaFileUpload(
                str(video_path),
                chunksize=-1,
                resumable=True
            )

            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            last_progress = 0
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress - last_progress >= 10:  # 每10%显示一次
                        console.print(f"   上传进度：{progress}%")
                        last_progress = progress

            video_id = response.get("id")
            if video_id:
                console.print(f"[green]✅ YouTube 上传成功！[/green]")
                console.print(f"   视频链接: https://www.youtube.com/watch?v={video_id}")
                return video_id
            else:
                console.print(f"[red]❌ 上传失败：未获取到 video_id[/red]")
                return None

        except Exception as e:
            console.print(f"[red]❌ YouTube 上传失败: {e}[/red]")
            return None

    # ================== 抖音下载相关方法 ==================

    def extract_user_id(self, url: str) -> Optional[str]:
        """从URL中提取用户ID"""
        patterns = [
            r'/user/([\w-]+)',
            r'sec_uid=([\w-]+)',
            r'MS4wLjABAAAA[\w-]+',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                user_id = match.group(1) if '(' in pattern else match.group(0)
                return user_id
        return None

    def get_single_video_info(self, aweme_id: str) -> Optional[Dict]:
        """获取单个视频的最新信息"""
        try:
            api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/"
            params = {'item_ids': aweme_id}

            self.rate_limiter.wait_if_needed()
            response = self.session.get(api_url, params=params, timeout=15)

            # 检查响应状态
            if response.status_code != 200:
                console.print(f"[yellow]⚠️  API返回错误状态码: {response.status_code}[/yellow]")
                if response.status_code in [401, 403]:
                    console.print(f"[red]❌ Cookie可能已过期，请更新Cookie后重试！[/red]")
                return None

            # 检查响应内容是否为空
            if not response.text or len(response.text.strip()) == 0:
                console.print(f"[yellow]⚠️  API返回空响应，Cookie可能已过期[/yellow]")
                return None

            # 尝试解析JSON
            try:
                data = response.json()
            except json.JSONDecodeError as je:
                console.print(f"[yellow]⚠️  JSON解析失败: {je}[/yellow]")
                console.print(f"[dim]响应内容前100字符: {response.text[:100]}[/dim]")
                if "登录" in response.text or "login" in response.text.lower():
                    console.print(f"[red]❌ 检测到需要登录，Cookie已过期！[/red]")
                return None

            # 检查返回数据
            if 'item_list' in data and len(data['item_list']) > 0:
                return data['item_list'][0]
            else:
                console.print(f"[yellow]⚠️  API返回数据中没有视频信息[/yellow]")
                if 'status_code' in data and data['status_code'] != 0:
                    console.print(f"[yellow]   API状态码: {data.get('status_code')}, 消息: {data.get('status_msg', 'N/A')}[/yellow]")
            return None

        except requests.exceptions.Timeout:
            console.print(f"[yellow]⏱️  请求超时，请检查网络连接[/yellow]")
            return None
        except requests.exceptions.RequestException as re:
            console.print(f"[yellow]⚠️  网络请求失败: {re}[/yellow]")
            return None
        except Exception as e:
            console.print(f"[yellow]⚠️  获取视频信息失败: {e}[/yellow]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
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

                if response.status_code != 200:
                    break

                # 处理 gzip
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    if response.content[:2] == b'\x1f\x8b':
                        import gzip
                        decompressed = gzip.decompress(response.content)
                        data = json.loads(decompressed.decode('utf-8'))
                    else:
                        break

                aweme_list = data.get('aweme_list', [])
                if not aweme_list:
                    break

                videos.extend(aweme_list)
                console.print(f"[green]已获取第{page}页，共{len(aweme_list)}个视频，累计{len(videos)}个[/green]")

                has_more = data.get('has_more', False)
                max_cursor = data.get('max_cursor', 0)

                if max_count > 0 and len(videos) >= max_count:
                    videos = videos[:max_count]
                    break

                page += 1
                time.sleep(1.0)

            except Exception as e:
                console.print(f"[red]获取视频列表异常: {e}[/red]")
                break

        console.print(f"[green]共获取到 {len(videos)} 个视频[/green]")
        return videos

    def get_video_download_url(self, aweme_info: Dict) -> Optional[str]:
        """提取无水印下载地址"""
        try:
            video_data = aweme_info.get('video', {})
            play_addr = video_data.get('play_addr', {})

            if play_addr and 'url_list' in play_addr:
                url = play_addr['url_list'][0]
                url = url.replace('playwm', 'play')
                url = url.replace('720p', '1080p')
                return url

            download_addr = video_data.get('download_addr', {})
            if download_addr and 'url_list' in download_addr:
                return download_addr['url_list'][0]

            return None
        except Exception as e:
            return None

    def sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        if len(filename) > 200:
            filename = filename[:200]
        return filename.strip()

    def download_single_video(self, video_info: Dict, index: int) -> Optional[Path]:
        """下载单个视频到临时目录"""
        try:
            aweme_id = video_info.get('aweme_id', '')
            desc = video_info.get('desc', '无标题')

            # 构建临时文件名
            filename = f"{index}_{aweme_id}_{self.sanitize_filename(desc[:50])}.mp4"
            save_path = self.temp_download_path / filename
            json_path = save_path.with_suffix('.json')

            # 获取下载地址
            download_url = self.get_video_download_url(video_info)
            if not download_url:
                console.print(f"[yellow]无法获取下载地址，跳过[/yellow]")
                return None

            console.print(f"[cyan]📥 下载视频: {desc[:50]}...[/cyan]")

            # 下载视频
            headers = {
                'Referer': 'https://www.douyin.com/',
                'User-Agent': self.headers['User-Agent']
            }

            max_retries = 3
            for retry in range(max_retries):
                try:
                    if retry > 0:
                        # 刷新链接
                        console.print(f"[yellow]🔄 尝试刷新下载链接 (第{retry}次重试)...[/yellow]")
                        fresh_info = self.get_single_video_info(aweme_id)
                        if fresh_info:
                            fresh_url = self.get_video_download_url(fresh_info)
                            if fresh_url:
                                download_url = fresh_url
                                video_info = fresh_info
                                console.print(f"[green]✅ 链接刷新成功[/green]")
                            else:
                                console.print(f"[red]❌ 无法获取新的下载链接[/red]")
                                break
                        else:
                            console.print(f"[red]❌ 无法刷新视频信息，可能Cookie已过期[/red]")
                            console.print(f"[yellow]💡 建议: 停止当前任务，更新Cookie后重新运行[/yellow]")
                            break

                    self.rate_limiter.wait_if_needed()
                    response = self.session.get(download_url, stream=True, timeout=60, headers=headers)
                    response.raise_for_status()

                    # 保存视频
                    temp_path = save_path.with_suffix('.tmp')
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)

                    temp_path.rename(save_path)

                    # 保存 JSON
                    json_path.write_text(
                        json.dumps(video_info, ensure_ascii=False, indent=2),
                        encoding='utf-8'
                    )

                    console.print(f"[green]✅ 下载成功[/green]")
                    self.stats.add_success()
                    return save_path

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 403 and retry < max_retries - 1:
                        console.print(f"[yellow]⚠️  403错误: 链接已过期或被拒绝[/yellow]")
                        time.sleep(2)
                        continue
                    elif e.response.status_code == 403:
                        console.print(f"[red]❌ 403错误: 重试{max_retries}次后仍然失败[/red]")
                        raise
                    else:
                        raise
                except Exception as e:
                    if retry < max_retries - 1:
                        console.print(f"[yellow]⚠️  下载出错: {e}, 将重试...[/yellow]")
                        time.sleep(2)
                        continue
                    else:
                        raise

            return None

        except Exception as e:
            console.print(f"[red]❌ 下载失败: {e}[/red]")
            self.stats.add_failed()
            return None

    def verify_cookie(self) -> bool:
        """验证Cookie是否有效"""
        console.print("[cyan]🔍 正在验证Cookie有效性...[/cyan]")
        try:
            # 尝试访问一个简单的API接口
            test_url = "https://www.douyin.com/aweme/v1/web/aweme/post/"
            params = {
                'device_platform': 'webapp',
                'aid': '6383',
                'count': '1',
            }
            response = self.session.get(test_url, params=params, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()
                    # 如果能成功解析JSON，说明Cookie基本有效
                    console.print("[green]✅ Cookie验证通过[/green]")
                    return True
                except:
                    pass

            console.print("[red]❌ Cookie验证失败，请更新Cookie！[/red]")
            console.print("[yellow]💡 提示: 请参考 COOKIE_GUIDE.md 重新获取Cookie[/yellow]")
            return False

        except Exception as e:
            console.print(f"[yellow]⚠️  Cookie验证时出错: {e}[/yellow]")
            return False

    def process_user_videos(self, url: str):
        """处理用户视频：下载 → 上传 → 删除"""
        console.print(f"[bold cyan]开始处理用户主页: {url}[/bold cyan]")

        # 验证Cookie
        if not self.verify_cookie():
            console.print("[red]❌ 请更新Cookie后重试[/red]")
            return

        # 提取用户ID
        user_id = self.extract_user_id(url)
        if not user_id:
            console.print("[red]无法提取用户ID[/red]")
            return

        console.print(f"[cyan]用户ID: {user_id}[/cyan]")

        # 获取视频列表
        max_count = self.config.get('max_count', 0)
        videos = self.get_user_videos(user_id, max_count)

        if not videos:
            console.print("[yellow]未获取到任何视频[/yellow]")
            return

        # 反转为从老到新
        if self.config.get('oldest_first', True):
            videos.reverse()
            console.print(f"[cyan]将从最老的视频开始处理[/cyan]")

        self.stats.total = len(videos)

        console.print(f"\n[bold green]开始处理 {len(videos)} 个视频...[/bold green]\n")

        # 逐个处理
        for idx, video in enumerate(videos, 1):
            try:
                aweme_id = video.get('aweme_id', '')
                desc = video.get('desc', '无标题')

                console.print(f"\n{'='*60}")
                console.print(f"[bold cyan]处理第 {idx}/{len(videos)} 个视频[/bold cyan]")
                console.print(f"[cyan]标题: {desc[:50]}...[/cyan]")

                # 检查是否已上传
                if aweme_id in self.uploaded_ids:
                    console.print(f"[yellow]⏭️  已上传过，跳过[/yellow]")
                    continue

                # 1. 下载视频
                video_path = self.download_single_video(video, idx)
                if not video_path:
                    continue

                # 2. 上传到 YouTube
                video_id = self.upload_to_youtube(video_path, video)

                if video_id:
                    # 3. 记录已上传
                    self.uploaded_ids.add(aweme_id)
                    self.save_uploaded_ids()
                    self.stats.add_uploaded()

                    # 4. 删除本地文件
                    video_path.unlink()
                    video_path.with_suffix('.json').unlink()
                    console.print(f"[green]🗑️  已删除本地文件，节省空间[/green]")
                else:
                    console.print(f"[red]⚠️  上传失败，保留本地文件[/red]")

                # 5. 间隔时间（可选）
                upload_interval = self.config.get('upload_interval_seconds', 0)
                if upload_interval > 0 and idx < len(videos):
                    console.print(f"[yellow]⏳ 等待 {upload_interval} 秒后继续...[/yellow]")
                    time.sleep(upload_interval)

            except KeyboardInterrupt:
                console.print("\n[yellow]用户中断[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]处理视频时出错: {e}[/red]")
                continue

        # 打印统计
        console.print(f"\n[bold green]处理完成！[/bold green]")
        console.print(f"总计: {self.stats.total}")
        console.print(f"下载成功: {self.stats.success}")
        console.print(f"上传成功: {self.stats.uploaded}")
        console.print(f"失败: {self.stats.failed}")
        console.print(f"耗时: {self.stats.get_elapsed_time():.2f}秒")


def load_config(config_path: Optional[str] = None) -> Dict:
    """加载配置文件"""
    if config_path and Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    return {
        'temp_path': './temp_download',
        'max_count': 0,
        'cookie': '',
        'oldest_first': True,
        'upload_interval_seconds': 0,  # 每个视频上传后的等待时间
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='抖音视频下载 + YouTube 自动上传')
    parser.add_argument('-u', '--url', type=str, help='用户主页链接')
    parser.add_argument('-c', '--config', type=str, help='配置文件路径')
    parser.add_argument('--cookie', type=str, help='抖音Cookie')
    parser.add_argument('--max-count', type=int, help='最大处理数量')
    parser.add_argument('--upload-interval', type=int, help='上传间隔（秒）')

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 命令行覆盖配置
    if args.cookie:
        config['cookie'] = args.cookie
    if args.max_count is not None:
        config['max_count'] = args.max_count
    if args.upload_interval is not None:
        config['upload_interval_seconds'] = args.upload_interval

    # 获取URL
    url = args.url or config.get('url')
    if not url:
        console.print("[red]错误: 请提供用户主页链接[/red]")
        sys.exit(1)

    try:
        uploader = DouyinYouTubeUploader(config)
        uploader.process_user_videos(url)
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断[/yellow]")
    except Exception as e:
        console.print(f"[red]程序异常: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
