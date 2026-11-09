# 移动端媒体优化交付说明

## 页面行为

- 商品列表按实际显示尺寸选择 WebP 缩略图。前两张有封面的商品图片立即加载，首张高优先级，其余懒加载。处理失败、旧文件或不支持 WebP 时使用原文件；加载失败可重试。
- 详情使用响应式图片，已知尺寸预留空间，首图优先、后续图片懒加载，点击预览读取原图。
- 详情视频先显示海报。点击播放或海报前，`video` 和嵌套 `source` 都不绑定下载地址；选择清晰度也不触发下载。播放后可选择流畅/高清、拖动进度、使用原生控件。
- 派生视频失败时尝试原文件；所有候选源失败或起播超时提供重试。切换路由时释放视频下载、监听器及在途请求。
- 商品主体不等待标题配置和评价请求；评价单独加载、失败可重试。保留会话校验、浏览计数、筛选、返回列表状态和评价提交。

本次沿用现有 Vue 页面、配色与导航。新增控件不引入动画、字体或第三方 UI 依赖。媒体处理集中在后端服务，前端共享 `MediaAsset` 契约；状态文件和 JSON 回填报告供开发人员和 Agent 排查。

## 上线与历史文件

服务端需安装更新后的 `backend/requirements.txt`，并提供 FFmpeg/ffprobe。Dockerfile 已包含 FFmpeg。原文件和数据库结构不变，新的上传自动处理，历史文件需要回填：

```powershell
python backend/media_cli.py --root '实际上传目录' --check-tools
python backend/media_cli.py --root '实际上传目录' --dry-run
python backend/media_cli.py --root '实际上传目录' --apply
```

详见 [媒体处理与运维](mobile-media-backend.md)，包括 Windows、Docker、PyInstaller、断点续跑与故障恢复。

当前工作区默认上传目录没有历史媒体；测试使用独立的 `output/media-review/uploads` 合成样本。未连接生产数据库、修改线上配置或执行线上回填。FFmpeg 测试工具位于被 Git 忽略的 `output/media-tools`；部署不可依赖此测试路径。

## 可复现验证

后端（配置 `MEDIA_FFMPEG` / `MEDIA_FFPROBE` 后包含真实视频测试）：

```powershell
python -m pytest backend/test_media_assets.py backend/test_upload.py backend/test_mobile_session.py -q -p no:cacheprovider
```

浏览器单元/页面回归：先在 `frontend-mobile` 运行 `npm run dev -- --host 127.0.0.1`，另一个终端从项目根目录运行：

```powershell
python -m pytest frontend-mobile/tests/test_media_browser.py -q -p no:cacheprovider
```

需要 Python Playwright 和 Chromium 或 Edge；可以通过 `BROWSER_EXECUTABLE` 指定本机浏览器。`MOBILE_TEST_URL` 可覆盖默认 Vite 地址 `http://127.0.0.1:5174`。这些用例使用独立请求夹具，不访问业务数据库。

生产构建与真实媒体冒烟：

```powershell
npm --prefix frontend-mobile run build
python frontend-mobile/tests/media_fixture.py
# 保持上面的隔离服务运行，另一个终端执行：
python frontend-mobile/tests/media_smoke.py
```

隔离服务只监听 `127.0.0.1:5015`，使用生产构建、真实生成图片与 FFmpeg 视频，检查图片原图预览、无点击不下载视频、播放/切换清晰度/拖动、导航和控制台错误。报告与截图位于 `output/media-review`。

## 样本结果与边界

2026-11-10 的合成样本，390×844、DPR 2、下载 1Mbps、延迟 300ms。比较的是同一新页面使用原图与使用压缩版本，不是线上旧版本的完整对比。最终复验首次访问前两张商品图片就绪约 **16.2 秒 → 4.1 秒**；同三张样本原图与 320px 版本的编码体积约 **1.54MB → 30.6KB**。两组热缓存均命中浏览器缓存。真实收益取决于原始素材、服务器、网络及终端，应上线后复测。

Lighthouse 13.6.0 在隔离列表页的默认移动端模拟下：性能 81、无障碍 94、LCP 3.2 秒、CLS 0、TBT 480ms。此模拟条件与上述固定网络不同，不混用指标，也不代表已达到 LCP 2.5 秒目标。已有页面仍有部分文字对比度与缺少 main 地标的问题，未在本次媒体性能改动中进行整页重设计。

最终后端与浏览器回归合计 **69 passed、1 skipped**；跳过项为 Windows 符号链接权限，另有一条已有 `datetime.utcnow()` 弃用警告。筛选规则测试、生产构建、新媒体工具的严格 TypeScript 检查通过。真实视频播放/切换/拖动、评价提交、返回列表筛选保留及控制台错误检查通过。

全量 `vue-tsc --noEmit` 仍有两处基线已有问题：`src/api/http.ts:15` 的 Axios headers 类型、`src/utils/baiduGeo.ts:51` 的百度地图构造器类型（已与 HEAD 源码核对，文件未改动）。Docker 镜像与 PyInstaller 成品未在本机构建。
