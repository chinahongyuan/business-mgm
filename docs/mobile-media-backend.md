# 移动端媒体处理与运维

原上传文件和 URL 保持不变。图片上传后生成 WebP；视频先返回可用的原文件 URL，再由后台队列生成海报和 MP4。数据库结构不变。列表、详情和历史记录只读取媒体元数据，不启动编码。

## API 和处理入口

- 上传响应保留 `data.url`、`data.name`，增加 `data.media`、`data.mediaStatus`。
- 商品列表和浏览历史增加 `coverMedia`；商品详情增加 `coverMedia` 和 `detailMedia`。`detailHtml` 保持原值。
- `detailMedia` 以 HTML 中 `img`、`video`、`source` 的 `src` 属性值为键（与浏览器读取属性时相同，HTML 实体已解码）。外链、缺失文件、无效元数据、动画和未完成的处理返回 `null`。
- `MediaAsset` 为 `{ original, width, height, images?, poster?, videos? }`。图片变体为 `{ url, width, height, bytes }`，视频变体另有 `label`。尺寸是实际输出像素；视频按低清到高清排列。
- `app.services.media_assets.process_media(path, root=None)` 同步生成并返回包含 `status`、`media`、`reason` 的记录；适合脚本和测试。
- `enqueue_media(path, root=None)` 用于上传：图片同步，视频异步；`get_media(url, root=None)` 与 `detail_media(html, root=None)` 为只读查询。
- `media_status(path, root=None)` 检查当前状态，`check_tools()` 检查工具路径。未指定 `root` 时使用 `UPLOAD_DIR` 或原有开发/打包上传目录。

图片目标宽度为 320、640、720、1080，跳过比原图更大的尺寸；原图不足 320 像素时保留实际宽度。修正 EXIF 方向，WebP 质量 80。动画 GIF/WebP 使用原文件，避免丢失动画。单张图片最多 4,000 万像素。

视频生成 H.264 / AAC MP4，`faststart` 元数据前置。目标为短边 480 和 720 像素，不放大，小视频去除重复尺寸。读取 SAR（像素宽高比）并缩减一条轴以归一为方形像素，再应用旋转方向，避免老视频被拉伸；视频、海报和元数据都使用该显示比例。H.264 输出尺寸向下取偶数，可能存在不足 2 像素的比例舍入差。`480p`、`720p` 是档位名称，实际尺寸以元数据为准。视频最多 30 分钟、4,000 万像素；ffprobe 超时 30 秒，每次 FFmpeg 调用超时 600 秒；每个编码进程使用 2 个编码线程。

探测和编码都在打开文件前固定输入容器：`.mp4` / `.mov` 使用 MOV demuxer，`.webm` 使用 Matroska demuxer；不允许自动识别成 DASH/HLS 等可引用其他文件的播放列表。仅允许 `file` 协议，并明确禁用 MOV 外部轨道和绝对路径别名。扩展名与实际容器不匹配的文件处理失败，仍保留原上传 URL。仅限制协议不足以限制本地文件访问，因此容器约束在 ffprobe 和 FFmpeg 两处分别执行。

## 部署依赖

```powershell
python -m pip install -r backend/requirements.txt
$env:MEDIA_FFMPEG = 'C:\tools\ffmpeg\bin\ffmpeg.exe'
$env:MEDIA_FFPROBE = 'C:\tools\ffmpeg\bin\ffprobe.exe'
python backend/media_cli.py --check-tools
```

`MEDIA_FFMPEG` 和 `MEDIA_FFPROBE` 可使用绝对路径；未设置时从系统 `PATH` 查找。两个程序都需要，FFmpeg 需支持 `libx264`、AAC 和 WebP。缺失工具或编码失败记录为 `failed`，上传和原文件访问仍可使用。服务器运行期间修正工具路径后，可以执行回填重试失败项；环境变量变更需要重启服务器。

Dockerfile 已在 Python 运行阶段安装 Debian `ffmpeg`（包含 ffprobe），Pillow 随 Python 依赖安装。容器上传目录仍应挂载持久化卷；`_media` 与原文件在同一上传根目录下。

PyInstaller 构建环境需要安装更新后的 requirements，Pillow 由常规 PyInstaller hooks 收集。FFmpeg/ffprobe **不会**自动打入 exe，需随部署提供独立可执行文件或配置系统 PATH；打包服务器的上传位置仍为 exe 相邻 `data/uploads`（可用 `UPLOAD_DIR` 覆盖）。回填 CLI 需在安装了 backend 依赖的 Python 环境运行，并用 `--root` 指向该目录。当前任务未运行 Docker 镜像或 PyInstaller 成品验证。

## 历史文件回填

在项目根目录执行，不连接数据库、不修改原文件、不删除媒体：

```powershell
python backend/media_cli.py --root 'D:\media\uploads' --check-tools
python backend/media_cli.py --root 'D:\media\uploads' --dry-run
python backend/media_cli.py --root 'D:\media\uploads' --apply
```

不传模式时默认 `--dry-run`，不创建目录或元数据。输出单个 JSON 对象，包含 `mode`、`root`、`tools`、`items` 和 `counts`；每个文件有 `source`、`status`、`reason`，便于 Agent 或运维脚本核验。`--check-tools` 缺少工具退出码为 2；`--apply` 有失败项退出码为 1；其余为 0。`--apply` 顺序处理，已就绪且有效的文件直接复用，失败、未完成、过期或丢失派生文件会重试；支持中断后重新运行同一命令。符号链接、生成文件和 `_media` 内部工作目录不参与历史扫描。名为 `_media` 的商品仍可上传，其目录中符合旧上传格式的 UUID 原文件保持公开访问，也参与生成和回填。

## 队列、恢复和缓存

每个服务器进程一个后台编码 worker，最多 8 个等待任务。队列满仍接受原上传，写入 `pending` 和原因；空闲时重新扫描待处理记录，扫描间隔至少 30 秒。启动时扫描旧 `pending` / `processing` 视频并恢复。异常记录 `failed` 和原因，避免循环重试坏文件；使用 CLI 重试。OS 文件锁在进程退出时自动释放，避免同一源文件被上传队列和回填同时处理。多进程部署会各有一个 worker，应按主机容量选择 WSGI worker 数量。

元数据原子替换，包含格式版本、源文件路径、大小/修改时间签名、源 SHA-256、处理状态和错误原因。读取时验证源签名、字段、派生文件位置及大小；元数据损坏或过期时回退原文件。派生文件名包含源内容 SHA-256、处理版本、档位与输出内容 SHA-256；更新原文件会产生新的派生 URL。处理版本当前为 `3`（包含 SAR 比例保持和输入容器约束），旧版本元数据需回填，旧生成 URL 仍可访问。改变编码策略时应升级版本。

只有 `_media` 中符合生成命名规则的文件及 UUID 命名的原上传使用 `public, max-age=31536000, immutable`；其他历史原文件使用 `no-cache, max-age=0, must-revalidate`。不要在原 UUID URL 下覆盖文件；更新媒体应重新上传。源签名检查依赖文件大小/修改时间，外部维护程序不得覆盖文件后再恢复旧修改时间。Range/206、条件请求和 CORS 保留；API 继续使用 `no-store`。元数据、锁、临时文件不通过 `/uploads` 暴露；路径解析阻止目录穿越和逃逸上传目录的符号链接。

处理被强制中止时可能留下临时目录或未被元数据引用的派生文件；它们不会被页面引用，也不会覆盖原文件。本功能不自动删除这些文件，磁盘清理需单独规划。

## 验证

```powershell
python -m pytest backend/test_media_assets.py backend/test_upload.py backend/test_mobile_session.py -q -p no:cacheprovider
```

测试涵盖原文件哈希、实际 WebP 像素尺寸、不放大、动画回退、过期/损坏元数据、路径约束、上传与列表契约、队列满和异常恢复、CLI 只读检查/断点续跑、缓存与 Range。存在 FFmpeg/ffprobe 时还运行真实 MP4/MOV/WebM 转码、SAR/旋转比例和 faststart 验证，并确认伪装成视频的 DASH 无法通过相对或绝对路径引用上传目录外的文件；探测和编码分别验证。Windows 未授予符号链接权限时相关实文件测试标记跳过。
