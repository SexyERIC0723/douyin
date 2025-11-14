# 抖音视频下载器 V2.0

一个功能强大的抖音视频批量下载工具，支持下载用户主页的所有视频。

## 功能特性

- ✅ 批量下载用户主页视频
- ✅ 自动解析短链接
- ✅ 无水印视频下载
- ✅ 智能限流避免请求过快
- ✅ 断点续传（跳过已下载文件）
- ✅ 美观的进度显示
- ✅ 详细的下载统计
- ✅ 保存视频元数据信息
- ✅ 支持配置文件和命令行参数

## 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install requests pyyaml rich python-dateutil
```

## 快速开始

### 方式一：命令行参数（推荐）

```bash
# 基本用法 - 下载用户所有视频
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..."

# 指定保存路径
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..." -p "./我的下载"

# 限制下载数量（只下载最新的50个视频）
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..." --max-count 50

# 使用Cookie（某些情况下需要）
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..." --cookie "你的Cookie"
```

### 方式二：配置文件

1. 编辑 `config.yml` 文件，填入相关配置
2. 运行：

```bash
python downloader.py -c config.yml
```

## 获取用户主页链接

### 方法1: 从抖音App分享

1. 打开抖音App
2. 进入要下载视频的用户主页
3. 点击右上角"..."按钮
4. 选择"分享" → "复制链接"
5. 得到类似 `https://v.douyin.com/xxxxx/` 的短链接

### 方法2: 从抖音网页版

1. 在电脑浏览器打开 https://www.douyin.com
2. 搜索并进入目标用户主页
3. 复制浏览器地址栏的链接
4. 得到类似 `https://www.douyin.com/user/MS4wLjABAAAA...` 的链接

**支持的链接格式：**
- `https://www.douyin.com/user/MS4wLjABAAAA...`
- `https://v.douyin.com/xxxxx/` （短链接）
- 包含 `sec_uid` 参数的链接

## 如何获取Cookie（重要！）

**抖音需要登录状态才能获取用户视频列表，因此Cookie是必需的！**

### 快速方法

1. 在浏览器中打开 https://www.douyin.com 并登录
2. 按 F12 打开开发者工具
3. 切换到 "Network"（网络）标签
4. 刷新页面（F5）
5. 点击任意请求
6. 在右侧找到 "Request Headers"（请求标头）
7. 找到 "Cookie" 字段，复制整个值
8. 将Cookie值填入配置文件或通过 `--cookie` 参数传入

### 详细图文教程

如果你是第一次获取Cookie，建议查看详细教程：[COOKIE_GUIDE.md](COOKIE_GUIDE.md)

该教程包含：
- 分步骤截图说明
- 不同浏览器的操作方法
- 常见问题解答
- 安全注意事项

## 配置文件说明

`config.yml` 文件示例：

```yaml
# 用户主页链接
url: "https://www.douyin.com/user/MS4wLjABAAAA..."

# 下载保存路径
path: "./Downloaded"

# 最大下载数量（0表示不限制）
max_count: 0

# Cookie（可选）
cookie: "你的Cookie值"
```

## 命令行参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `-u, --url` | 用户主页链接 | `-u "https://www.douyin.com/user/..."` |
| `-c, --config` | 配置文件路径 | `-c config.yml` |
| `-p, --path` | 下载保存路径 | `-p "./我的下载"` |
| `--cookie` | 抖音Cookie | `--cookie "msToken=..."` |
| `--max-count` | 最大下载数量 | `--max-count 50` |

## 下载目录结构

```
Downloaded/
└── MS4wLjABAAAA.../          # 用户ID文件夹
    ├── 1_视频ID_视频标题.mp4   # 视频文件
    ├── 1_视频ID_视频标题.json  # 视频元数据
    ├── 2_视频ID_视频标题.mp4
    ├── 2_视频ID_视频标题.json
    └── ...
```

## 注意事项

1. **请求频率限制**：程序内置了限流机制（每秒最多2个请求），避免请求过快被封禁

2. **Cookie有效期**：Cookie有时效性，如果下载失败提示需要登录，请重新获取Cookie

3. **网络稳定性**：下载大量视频时，建议保持网络稳定，程序会自动跳过已下载的文件

4. **视频数量限制**：
   - 使用 `--max-count` 参数可限制下载数量
   - 设置为 `0` 表示下载所有视频（默认）

5. **文件命名**：
   - 视频文件名格式：`序号_视频ID_视频标题.mp4`
   - 文件名会自动过滤非法字符
   - 标题过长会自动截断

6. **断点续传**：
   - 程序会自动跳过已存在的文件
   - 中断后重新运行会继续下载未完成的视频

## 常见问题

### Q: 提示"未获取到任何视频"？

**A:** 可能的原因：
- 用户主页没有公开视频
- 需要登录才能查看，请提供Cookie
- Cookie已过期，请重新获取
- 网络问题，请检查网络连接

### Q: 下载速度很慢？

**A:**
- 这是正常现象，程序内置了限流保护
- 抖音服务器的下载速度也会影响
- 建议在网络条件好的环境下使用

### Q: 下载的视频有水印？

**A:**
- 程序会自动尝试获取无水印链接
- 如果仍有水印，可能是API返回的链接本身带水印
- 可以尝试更新Cookie或稍后重试

### Q: 支持下载多个用户的视频吗？

**A:**
- 当前版本一次只能下载一个用户的视频
- 可以多次运行程序，每次指定不同的用户链接

## 技术特性

- **智能限流**：RateLimiter 类控制请求频率，避免被封禁
- **断点续传**：自动检测并跳过已下载文件
- **进度显示**：使用 Rich 库提供美观的进度条和统计信息
- **元数据保存**：每个视频都会保存对应的JSON元数据文件
- **错误处理**：完善的异常处理机制，下载失败不影响后续视频
- **文件名清理**：自动处理文件名中的非法字符

## 参考项目

本项目参考了 [jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader) 的V2.0增强版实现。

## 免责声明

- 本工具仅供学习交流使用
- 请尊重视频创作者的版权
- 下载的视频仅限个人观看，请勿用于商业用途
- 使用本工具产生的任何法律问题与开发者无关

## 许可证

MIT License

## 更新日志

### V2.0 (2024-11-14)
- ✅ 初始版本发布
- ✅ 支持用户主页视频批量下载
- ✅ 美观的终端界面
- ✅ 完善的配置和命令行参数支持
