# 如何获取抖音Cookie - 详细图文教程

## 为什么需要Cookie？

抖音的Web API需要登录状态才能获取用户的视频列表。Cookie就是你的登录凭证，它告诉抖音服务器"这是一个已登录的用户"。

## 获取步骤（Chrome浏览器）

### 步骤1：登录抖音网页版
1. 打开Chrome浏览器
2. 访问 https://www.douyin.com
3. 点击右上角登录按钮
4. 使用手机扫码或账号密码登录

### 步骤2：打开开发者工具
- **方法1**：按键盘上的 `F12`
- **方法2**：右键点击页面 → 选择"检查"
- **方法3**：按 `Ctrl + Shift + I` (Windows) 或 `Cmd + Option + I` (Mac)

### 步骤3：切换到Network标签
1. 在开发者工具顶部找到 "Network" (网络) 标签
2. 点击切换到该标签

### 步骤4：刷新页面
- 按 `F5` 或点击浏览器的刷新按钮
- 你会看到Network标签中出现很多网络请求

### 步骤5：找到Cookie
1. 在左侧请求列表中，点击任意一个请求（建议选择 `aweme` 或 `post` 相关的请求）
2. 在右侧面板中找到 "Headers" (标头) 选项卡
3. 向下滚动找到 "Request Headers" (请求标头) 部分
4. 找到 `Cookie:` 这一行

### 步骤6：复制Cookie值
1. 点击Cookie后面的值（很长的一串字符）
2. 右键 → 选择"Copy value" (复制值)
3. 或者双击选中整个值，然后 `Ctrl+C` 复制

### Cookie示例
```
Cookie值看起来像这样（示例，不要直接使用）：
ttwid=1%7C...; passport_csrf_token=...; odin_tt=...; __ac_nonce=...; __ac_signature=...
```

## 使用Cookie的三种方式

### 方式1：通过命令行参数（推荐测试时使用）
```bash
python downloader.py -u "用户链接" --cookie "你复制的Cookie值"
```

### 方式2：通过配置文件（推荐长期使用）
编辑 `config.yml` 文件：
```yaml
url: "https://www.douyin.com/user/MS4wLjABAAAA..."
path: "./Downloaded"
max_count: 0
cookie: "你复制的Cookie值"  # 粘贴在这里
```

然后运行：
```bash
python downloader.py -c config.yml
```

### 方式3：程序运行时输入
如果不设置Cookie，程序会提示你，你可以根据提示获取后重新运行。

## 注意事项

### Cookie的有效期
- Cookie通常在一段时间后会过期
- 如果程序提示"Cookie已过期"，请重新获取
- 一般Cookie可以使用几天到几周不等

### 安全提醒
- **不要泄露你的Cookie给他人**，它等同于你的账号密码
- **不要在公共场合展示包含Cookie的截图**
- **不要把Cookie上传到公开的代码仓库**
- 使用完毕后，可以退出登录使Cookie失效

### Cookie格式检查
正确的Cookie应该：
- 包含多个键值对，用分号分隔
- 包含 `ttwid`、`passport_csrf_token` 等关键字段
- 长度通常在1000-3000个字符左右

## 常见问题

### Q1: 找不到Cookie字段？
**A**: 确保：
1. 已经登录了抖音
2. 刷新了页面（F5）
3. 在Request Headers（请求标头）中查找，不是Response Headers（响应标头）

### Q2: Cookie复制后不完整？
**A**:
- Cookie很长，确保完整复制
- 可以在文本编辑器中查看，确保开头和结尾都复制了
- 开头通常是 `ttwid=`
- 结尾通常是一串随机字符

### Q3: 提示Cookie无效？
**A**:
1. 检查是否完整复制
2. 检查是否有换行符或空格
3. 尝试重新登录后获取新Cookie
4. 确保复制的是Cookie值，不包含 `Cookie:` 这个标签本身

### Q4: 在Mac上如何操作？
**A**:
- 开发者工具快捷键：`Cmd + Option + I`
- 刷新页面：`Cmd + R`
- 其他步骤与Windows相同

## 其他浏览器

### Firefox
1. 按 `F12` 打开开发者工具
2. 切换到"网络"标签
3. 刷新页面
4. 点击任意请求
5. 在右侧"Headers"中找到Cookie

### Safari
1. 首先启用开发菜单：Safari → 偏好设置 → 高级 → 勾选"在菜单栏中显示开发菜单"
2. 开发 → 显示Web检查器
3. 切换到"网络"标签
4. 刷新页面并查找Cookie

### Edge
与Chrome步骤相同（Edge基于Chromium）

## 测试Cookie是否有效

运行程序后，查看输出：
```bash
✓ 已设置Cookie，长度: 2543
```

如果看到这行绿色的提示，说明Cookie已正确设置。

如果看到：
```bash
✗ 警告：未设置Cookie！
```

说明Cookie未设置或格式有误。

## 获取帮助

如果仍然遇到问题：
1. 检查是否已登录抖音网页版
2. 尝试退出登录后重新登录
3. 清除浏览器缓存后重试
4. 尝试使用无痕模式重新登录和获取Cookie
