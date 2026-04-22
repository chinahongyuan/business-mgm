# business-mgm

商家管理系统：管理后台（Vue 3）与 API（Flask）**同一进程、同一端口**发布，避免运维时分别启动两个服务。

## 架构

- **运行时**：Flask 提供 `GET /api/*` JSON 接口，同时托管构建后的管理端静态资源（`backend/app/static/admin`）。
- **构建时**：`frontend-admin` 执行 `npm run build`，产物输出到上述目录，与后端打成一个部署单元。

## 一键启动（推荐）

在项目根目录：

```bash
python start.py
```

会先执行前端构建，再启动 Flask（默认 `http://127.0.0.1:5000`）。浏览器打开根路径即可访问管理后台。

仅后端调试（前端已构建过）：

```bash
python start.py --skip-build
```

## 手动分步

```bash
cd frontend-admin
npm install
npm run build

cd ../backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python wsgi.py
```

## 配置

复制 `.env.example` 为 `backend/.env`（或在根目录 `.env`），按需修改数据库与密钥。

## 生产部署（单进程）

使用 Waitress 或 Gunicorn（Linux）挂载 `backend/wsgi:app` 即可；静态文件已由 Flask 托管，无需 Nginx 单独托管前端（仍可在前面加 Nginx 做反向代理与 TLS）。

示例（Windows / 跨平台）：

```bash
cd backend
pip install -r requirements.txt
cd ../frontend-admin && npm ci && npm run build
cd ../backend
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

## 开发说明（可选）

若需要前端热更新，可开两个终端：终端 A `cd backend && python wsgi.py`；终端 B `cd frontend-admin && npm run dev`（已配置将 `/api` 代理到 `127.0.0.1:5000`）。上线与日常联调仍以「单进程 + 构建产物」为准。
