# 抖音视频下载器 V2.3

一个功能强大的抖音视频批量下载工具，支持下载用户主页的所有视频，并可自动上传到YouTube。

## 功能特性

### 下载功能
- ✅ 批量下载用户主页视频
- ✅ 自动解析短链接
- ✅ 无水印视频下载
- ✅ **智能重试机制**（网络中断、403错误自动重试3次）
- ✅ 智能限流避免请求过快
- ✅ 断点续传（跳过已下载文件）
- ✅ **改进的错误处理**（JSON解析错误、空响应等）
- ✅ 美观的进度显示
- ✅ 详细的下载统计
- ✅ 保存视频元数据信息
- ✅ 支持配置文件和命令行参数

### YouTube集成功能（V2.3新增）
- ✅ **自动上传到YouTube**：下载后立即上传，无需手动操作
- ✅ **智能去重**：自动记录已上传视频，避免重复上传
- ✅ **节省空间**：上传完成后自动删除本地文件
- ✅ **按时间顺序处理**：从最老视频开始，保持视频发布顺序
- ✅ **可配置上传间隔**：避免触发YouTube API限制
- ✅ **完整的YouTube设置**：支持隐私、分类、儿童内容等所有选项

## 安装依赖

### 基础下载功能

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install requests pyyaml rich python-dateutil
```

### YouTube集成功能（可选）

如果需要使用YouTube自动上传功能，还需安装：

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## 快速开始

### 方式一：命令行参数（推荐）

```bash
# 基本用法 - 下载用户所有视频（默认从最老的视频开始）
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..."

# 指定保存路径
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..." -p "./我的下载"

# 限制下载数量（只下载最老的50个视频）
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..." --max-count 50

# 从最新的视频开始下载（而不是默认的最老开始）
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..." --newest-first

# 使用Cookie（必需的）
python downloader.py -u "https://www.douyin.com/user/MS4wLjABAAAA..." --cookie "你的Cookie"
```

### 方式二：配置文件

1. 编辑 `config.yml` 文件，填入相关配置
2. 运行：

```bash
python downloader.py -c config.yml
```

## YouTube集成模式（V2.3新增）

### 功能说明

`downloader_uploader.py` 是一个集成脚本，可以自动完成：下载视频 → 上传YouTube → 删除本地文件 的完整流程。

**特点**：
- 📥 下载一个视频 → 📤 立即上传YouTube → 🗑️ 删除本地文件 → 继续下一个
- 💾 节省磁盘空间：不会堆积大量本地视频文件
- 🔄 防止重复上传：自动记录已上传的视频ID
- ⏱️ 智能速率控制：可配置上传间隔，避免API限制
- 📊 按时间顺序处理：从最老的视频开始上传

### 前置准备

#### 1. 获取YouTube API凭证

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 "YouTube Data API v3"
4. 创建 OAuth 2.0 客户端ID
5. 下载客户端密钥JSON文件，重命名为 `client_secrets.json`
6. 将文件放在项目根目录

#### 2. 配置文件设置

编辑 `config_uploader.yml` 文件：

```yaml
# 抖音用户链接
url: "https://www.douyin.com/user/MS4wLjABAAAA..."

# 临时下载路径
temp_path: "./temp_download"

# Cookie（必需）
cookie: "你的抖音Cookie"

# YouTube客户端密钥文件
client_secrets_file: "client_secrets.json"

# 上传间隔（秒）- 建议5-10秒
upload_interval_seconds: 5

# 视频设置
privacy_status: "public"  # public/private/unlisted
made_for_kids: true       # 是否为儿童内容
category_id: "24"         # 24=娱乐
```

### 使用方法

```bash
# 使用配置文件运行（推荐）
python downloader_uploader.py -c config_uploader.yml

# 命令行参数方式
python downloader_uploader.py \
  -u "https://www.douyin.com/user/MS4wLjABAAAA..." \
  --cookie "你的Cookie" \
  --client-secrets client_secrets.json \
  --upload-interval 5
```

### 运行流程

1. **首次运行**：会打开浏览器要求授权YouTube访问权限
2. **授权完成**：开始处理视频
3. **处理过程**：
   - 获取用户所有视频列表（按时间从老到新）
   - 逐个处理：下载 → 上传 → 记录 → 删除
   - 显示实时进度和统计信息
4. **自动去重**：已上传的视频会跳过（根据`uploaded_videos.json`）
5. **断点续传**：中断后重新运行会继续未完成的视频

### 目录结构

```
项目根目录/
├── downloader_uploader.py      # 集成上传脚本
├── config_uploader.yml         # 上传配置文件
├── client_secrets.json         # YouTube API密钥
├── uploaded_videos.json        # 已上传视频记录（自动生成）
├── temp_download/              # 临时下载目录（自动清理）
└── token.pickle                # YouTube认证令牌（自动生成）
```

### 注意事项

1. **API配额限制**：
   - YouTube API每日有配额限制（默认10,000单位）
   - 每次上传消耗约1,600单位
   - 建议设置 `upload_interval_seconds: 5-10` 避免过快
   - 每日可上传约6个视频（根据配额）

2. **网络稳定性**：
   - 上传大文件需要稳定网络
   - 建议在网络条件好时运行
   - 上传失败会自动重试

3. **视频内容审核**：
   - YouTube会自动审核上传的视频
   - 违规内容可能导致频道被限制
   - 请确保上传内容符合YouTube社区准则

4. **儿童内容设置**：
   - `made_for_kids: true` 表示视频为儿童内容
   - 儿童视频会有功能限制（无评论、无推荐等）
   - 请根据实际内容正确设置

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

# 视频下载顺序
# true: 从最老的视频开始下载（推荐，按时间顺序）
# false: 从最新的视频开始下载
oldest_first: true

# Cookie（必需）
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
| `--oldest-first` | 从最老的视频开始下载（默认） | `--oldest-first` |
| `--newest-first` | 从最新的视频开始下载 | `--newest-first` |

## 下载目录结构

```
Downloaded/
└── MS4wLjABAAAA.../          # 用户ID文件夹
    ├── 1_视频ID_视频标题.mp4   # 第1个视频（默认为最老的视频）
    ├── 1_视频ID_视频标题.json  # 视频元数据
    ├── 2_视频ID_视频标题.mp4   # 第2个视频
    ├── 2_视频ID_视频标题.json
    └── ...
    └── 231_视频ID_视频标题.mp4 # 最后一个视频（最新的）
```

**文件编号规则**：
- 默认（`oldest_first: true`）：1号=最老视频，231号=最新视频（按时间顺序）
- 如设置 `oldest_first: false`：1号=最新视频，231号=最老视频（倒序）

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

### Q: 只下载了部分视频，没有下载全部？

**A:** 可能的原因和解决方案：
- **Cookie过期**：抖音Cookie有时效性，过期后API会返回空响应。解决：重新获取Cookie
- **API限流**：请求过快被限流。V2.1已增加请求间隔到1秒，大幅降低限流风险
- **网络问题**：网络不稳定导致请求失败。解决：检查网络连接，程序会自动重试
- **查看详细日志**：运行时会显示"已获取第X页，共X个视频"，查看是否有错误提示

**建议**：
1. 重新获取新的Cookie
2. 增加请求间隔（修改代码中的 `time.sleep(1.0)` 为更大值）
3. 分批下载（使用 `--max-count` 参数）

### Q: 某些视频下载失败（403或网络错误）？

**A:**
- **403 Forbidden - 链接过期**（常见于后期视频）
  - **原因**：抖音视频CDN链接有时效性（约1-2小时）
  - **表现**：前面视频正常，后面大量403错误
  - **解决**：V2.2已添加智能链接刷新功能
    - 遇到403时自动重新获取最新下载链接
    - 使用refreshed的链接重试下载
  - **建议**：下载大量视频时可分批进行

- **403 Forbidden - 防盗链**（个别视频）
  - V2.1已添加Referer请求头
  - 自动重试3次
  - 如仍失败，可能该视频链接确实无法访问

- **网络中断**：下载大文件时网络不稳定
  - V2.1已添加自动重试机制
  - 使用临时文件，下载完成才重命名，避免损坏
  - 增加了超时时间到60秒

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

- **智能限流**：RateLimiter 类控制请求频率，页面请求间隔1秒，避免被封禁
- **智能重试**：网络错误、403错误自动重试3次，递增延迟（2s、4s）
- **断点续传**：自动检测并跳过已下载文件
- **临时文件机制**：下载时使用.tmp文件，完成后才重命名，避免损坏
- **进度显示**：使用 Rich 库提供美观的进度条和统计信息
- **元数据保存**：每个视频都会保存对应的JSON元数据文件
- **完善错误处理**：
  - JSON解析错误自动处理
  - 空响应检测
  - 详细的错误日志和堆栈跟踪
  - 分类处理HTTP错误、网络错误
- **防盗链处理**：视频下载添加Referer请求头
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

### V2.3 (2024-11-16)
- 🎉 **YouTube自动上传集成**：全新的 `downloader_uploader.py` 脚本
  - 下载 → 上传 → 删除 全自动流程
  - 节省磁盘空间，无需手动管理本地文件
  - 智能去重，自动记录已上传视频
  - 可配置上传间隔，避免API限制
- ✅ **完整的YouTube设置**：支持隐私、分类、儿童内容等选项
- ✅ **新增配置文件**：`config_uploader.yml` 专用于集成模式
- ✅ **详细文档**：添加YouTube API设置和使用说明
- ✅ **OAuth认证**：支持Google账号授权，安全可靠

**新增功能**：
- 一键完成抖音视频搬运到YouTube
- 按时间顺序自动上传，保持视频发布顺序
- 断点续传，中断后继续未完成的视频

### V2.2 (2024-11-15)
- 🔥 **智能链接刷新**：解决大量视频下载时链接过期问题
  - 自动检测403错误并刷新下载链接
  - 添加 `get_single_video_info()` 方法获取最新视频信息
  - 大幅提高大批量下载的成功率
- 🎯 **视频下载顺序控制**：支持从最老或最新视频开始
  - 新增 `oldest_first` 配置选项（默认true，从最老开始）
  - 新增 `--oldest-first` 和 `--newest-first` 命令行参数
  - 方便按时间顺序整理视频
- ✅ **优化错误提示**：区分链接过期和防盗链的403错误
- ✅ **完善文档**：添加链接时效性问题的详细说明

**解决的问题**：
- 前期视频正常，后期大量403错误
- 下载200+视频时链接过期导致失败率高
- 默认从新到旧的顺序不符合按时间整理的需求

### V2.1 (2024-11-15)
- ✅ **修复用户ID提取bug**：支持包含连字符的sec_uid
- ✅ **改进API调用**：添加完整的请求参数，提高成功率
- ✅ **智能重试机制**：自动重试失败的下载（最多3次）
  - 403错误自动重试
  - 网络中断自动重试
  - 递增延迟避免频繁请求
- ✅ **改进错误处理**：
  - JSON解析错误处理
  - 空响应检测
  - 详细的错误日志
- ✅ **增加请求间隔**：从0.5秒增加到1秒，降低限流风险
- ✅ **临时文件机制**：使用.tmp文件避免下载中断导致文件损坏
- ✅ **防盗链处理**：添加Referer请求头
- ✅ **Cookie帮助**：未设置Cookie时显示详细获取指南
- ✅ **详细文档**：添加COOKIE_GUIDE.md和常见问题

### V2.0 (2024-11-14)
- ✅ 初始版本发布
- ✅ 支持用户主页视频批量下载
- ✅ 美观的终端界面
- ✅ 完善的配置和命令行参数支持
