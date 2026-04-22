# Docker 完整部署方案（business-mgm）

面向：**1Panel 已安装 Docker**、**已用 1Panel 创建 MySQL 容器**（示例：容器名 `mysql`、镜像 `mysql:8.0.x`、网络 `1panel-network`、库 `business_mgm`、端口映射 `3306`）、项目在服务器目录如 **`/home/management/business-mgm`**。

---

## 一、架构说明

| 组件 | 说明 |
|------|------|
| **镜像** | 多阶段构建：Node 构建管理端 + 移动端 → Python 3.12 运行 `run_server.py`（Waitress） |
| **Web 容器** | 仅本项目的 `web` 服务，**不包含**第二个 MySQL |
| **数据库** | 使用已有 MySQL 容器；Web 通过 **同一 Docker 网络** 用主机名 **`mysql:3306`** 连接（**不使用公网 IP**） |
| **上传文件** | 宿主机 `./data/uploads` 挂载到容器 `/app/data/uploads`，与 URL 前缀 `/uploads/` 一致 |

---

## 二、服务器前置检查

```bash
docker --version
docker ps | grep mysql
docker inspect mysql --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
docker port mysql 3306
```

记下 **网络名**（例如 `1panel-network`）和 MySQL **用户名**（常见为 `root`）。

**Docker Compose（必装其一）**

- 推荐 **Compose V2 插件**，命令为 **`docker compose`**（中间有空格）。检查：

  ```bash
  docker compose version
  ```

- 若提示 `compose` 不是子命令或 `unknown shorthand flag: 'd'`，说明未安装插件，在 CentOS/RHEL 上执行：

  ```bash
  dnf install -y docker-compose-plugin
  # 或: yum install -y docker-compose-plugin
  systemctl restart docker
  ```

- 旧版独立命令 **`docker-compose`**（带连字符）若已安装也可使用；项目里 `scripts/docker-up.sh` 会自动尝试两种命令。

---

## 三、目录与代码

```bash
mkdir -p /home/management
cd /home/management
# 任选其一：git clone 你的仓库；或上传压缩包后解压到 business-mgm
cd business-mgm
```

确保项目根目录包含：`Dockerfile`、`docker-compose.yml`、`backend/`、`frontend-admin/`、`frontend-mobile/`。

---

## 四、环境变量 `.env`

```bash
cp env.docker.example .env
nano .env
```

**推荐配置（与 mysql 同网，主机名 `mysql`）：**

```env
MYSQL_DOCKER_NETWORK=1panel-network

# 密码中含 @ : / 等须 URL 编码，例如 @ → %40
DATABASE_URL=mysql+pymysql://root:你的密码编码后@mysql:3306/business_mgm?charset=utf8mb4

WEB_PORT=5000
WAITRESS_THREADS=8
```

- **`MYSQL_DOCKER_NETWORK`**：必须与 `docker inspect mysql` 看到的网络名一致。  
- **`DATABASE_URL`**：主机必须是 **`mysql`**（与 `docker ps` 中容器名一致），**不要**写服务器公网 IP。

**可选：** 若使用根目录 `config.json`（百度地图等），把文件放在项目根目录，并在 `docker-compose.yml` 中取消 `config.json` 那一行 `volumes` 注释。

---

## 五、首次启动

```bash
cd /home/management/business-mgm
mkdir -p data/uploads
docker compose up -d --build
```

或一键（会自动复制 `env.docker.example` → `.env`，若尚未存在）：

```bash
chmod +x scripts/docker-up.sh
./scripts/docker-up.sh
```

查看日志：

```bash
docker compose logs -f web
```

**数据库初始化：** 若 1Panel 中**已导入**数据库与表，**一般不要**再执行 `init-db`。仅当确认是**空库**时：

```bash
docker compose run --rm web python run_server.py init-db
```

---

## 六、访问地址

- 移动端 H5：`http://服务器IP:WEB_PORT/`  
- 管理后台：`http://服务器IP:WEB_PORT/system-management`  

若 1Panel / Nginx 做了 **HTTPS 反代**，用域名访问即可；注意前后端 **同源** 或正确配置反代，避免 `/api`、`/uploads` 被错误拦截。

---

## 七、更新发版（修 Bug / 发新版本）

```bash
cd /home/management/business-mgm
git pull
docker compose up -d --build
```

MySQL 数据在独立容器/卷内，**不会**因重建 Web 镜像而丢失。上传文件在 **`data/uploads`**，只要挂载不变即保留。

---

## 八、备选：无法加入 `1panel-network` 时

若暂时不能把 Web 挂到与 `mysql` 相同的网络，可使用宿主机已映射的 `3306`（**仍不要用公网 IP**）：

1. `.env` 中把 `DATABASE_URL` 主机改为 **`host.docker.internal`**，端口仍为 `3306`，密码同样需 URL 编码。  
2. **不要**设置 `MYSQL_DOCKER_NETWORK`（备选 compose 不需要）。  
3. 使用：

```bash
docker compose -f docker-compose.host-gateway.yml up -d --build
```

---

## 九、常用命令

```bash
docker compose ps
docker compose logs -f web --tail 200
docker compose restart web
docker compose down          # 停止并删除本项目容器（不删 MySQL 容器）
```

---

## 十、排错要点

| 现象 | 方向 |
|------|------|
| `network ... external but could not be found` | 检查 `MYSQL_DOCKER_NETWORK` 是否与 `docker network ls` 一致 |
| 数据库连接失败 | 检查 `DATABASE_URL` 用户/密码/库名；密码是否已 URL 编码 |
| 图片/视频 404 | 检查宿主机 `data/uploads` 是否存在、挂载是否生效；库中 URL 是否为 `/uploads/...` |
| 构建很慢 | 构建机会下载 Node/Python 依赖，首次较慢属正常 |
| **`docker build` 卡在拉取 `node:20-alpine` / `Timeout` / 没有生成 `business-mgm` 镜像 | 构建**失败**则不会产生新镜像；多为访问 **Docker Hub** 超时（国内服务器常见）。见下文「拉取基础镜像失败」。 |

---

## 拉取基础镜像失败（Docker Hub 超时）

**现象**：`Get "https://registry-1.docker.io/v2/": ... Client.Timeout exceeded`，或构建结束后 **`docker images` 里没有 `business-mgm`**。

**原因**：第一步要从 Docker Hub 拉取 `node:20-alpine`、`python:3.12-slim-bookworm` 等；连不上 Hub 时构建中断，**不会**留下成品镜像。

**处理（任选其一或组合）**：

1. **配置镜像加速（推荐）**  
   编辑 `/etc/docker/daemon.json`（没有则新建），例如：

   ```json
   {
     "registry-mirrors": [
       "https://docker.1ms.run",
       "https://docker.xuanyuan.me"
     ]
   }
   ```

   镜像站地址会随时间变化，可在 1Panel「容器 → 配置」或云厂商文档里查当前可用地址。保存后执行：

   ```bash
   systemctl daemon-reload
   systemctl restart docker
   ```

2. **先单独测拉取**  

   ```bash
   docker pull node:20-alpine
   docker pull python:3.12-slim-bookworm
   ```

   成功后再执行：`bash scripts/build-docker-image.sh`

3. **网络稳定后重试**（偶发超时可直接再跑一次）。

4. **（可选）BuildKit**：若你在 shell 里执行了 `export DOCKER_BUILDKIT=1`，**必须先安装** `docker buildx`（否则构建会直接报错）。例如 CentOS/RHEL：

   ```bash
   dnf install -y docker-buildx-plugin
   # 或 yum install docker-buildx-plugin
   ```

   **未安装 buildx 时请不要设置 `DOCKER_BUILDKIT=1`**，直接 `bash scripts/build-docker-image.sh` 即可；`build-docker-image.sh` 会在检测到无 buildx 时自动取消 `DOCKER_BUILDKIT`。

5. **Dockerfile 已默认使用 DaoCloud 基础镜像 + 国内 pip/npm**（不访问 `registry-1.docker.io`）。直接：

   ```bash
   bash scripts/build-docker-image.sh
   ```

   若能直连 Docker Hub 且想用官方镜像：`USE_OFFICIAL_HUB=1 bash scripts/build-docker-image.sh`。

   若仍失败，在服务器执行 `bash scripts/docker-network-check.sh`，把输出贴给维护者；并尝试手动 `docker pull docker.m.daocloud.io/library/node:20-alpine` 看是否超时。

   若 DaoCloud 也被墙/限速，只能换**其他 Hub 代理地址**（改 `Dockerfile` 里 `NODE_IMAGE` / `PYTHON_IMAGE` 默认值），或在一台能上网的机器 `docker save` 后拷贝 `docker load`。

**说明**：列表里 **`REPOSITORY <none>`** 多为**未完成构建**产生的悬空层，可用 `docker image prune -f` 清理；与本次失败无直接关系。

---

## 十一、仅生成 Docker 镜像（不上线 compose）

**若执行脚本提示「没有那个文件或目录」「bad interpreter」「set: 无效选项」「EXTRA_ARGS 未绑定」等**：多为脚本带 **CRLF（Windows 换行）**。在服务器执行：

```bash
sed -i 's/\r$//' scripts/*.sh
# 或: dos2unix scripts/*.sh
```

仓库根目录已增加 **`.gitattributes`**（`*.sh` 强制 **LF**），用 **Git clone/pull** 拉代码时 Linux 上一般为 LF；若仍用 zip 从 Windows 上传，需再执行一次上面的 `sed`。

然后使用 **`bash scripts/build-docker-image.sh`**（推荐）。

源代码放在例如 `/home/xt/server/BUSINESS-MGM` 后：

```bash
cd /home/xt/server/BUSINESS-MGM
chmod +x scripts/build-docker-image.sh
./scripts/build-docker-image.sh
```

会生成标签 `business-mgm:<日期时间>` 与 `business-mgm:latest`。  
Windows 开发机：`.\scripts\build-docker-image.ps1`

可选：`COMPOSE_TOO=1 ./scripts/build-docker-image.sh` 同时执行 `docker compose build`。

---

## 十二、与本仓库文件的对应关系

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 多阶段构建镜像 |
| `docker-compose.yml` | 主方案：外挂 MySQL 网络 + `mysql` 主机名 |
| `docker-compose.host-gateway.yml` | 备选：`host.docker.internal` |
| `env.docker.example` | 复制为 `.env` 的模板 |
| `.dockerignore` | 减小构建上下文体积 |
| `scripts/build-docker-image.sh` | Linux：一键 `docker build` |
| `scripts/build-docker-image.ps1` | Windows：同上 |

本地或 CI 可在项目根目录执行：`docker build -t business-mgm:latest .` 仅打镜像；服务器上通常使用 `docker compose build` 即可。

---

## 十三、构建成功后：启动、访问、迁镜像

### 是否成功

日志末尾出现 **`Successfully built`**、**`Successfully tagged business-mgm:latest`**，且 `docker images` 中有 **`business-mgm`**，即表示**镜像已打好**。

### 日志里可忽略/可处理的项

| 现象 | 说明 |
|------|------|
| `DEPRECATED: The legacy builder...` | 提示将来可装 buildx；**不影响**当前镜像。 |
| `pip ... Running as the 'root' user` | 容器内以 root 装依赖是常见做法，**可忽略**。 |
| `REPOSITORY <none>` | 以往失败或中途层产生的**悬空镜像**，可 `docker image prune -f` 清理。 |

### 启动

**方式 A：`docker compose`（与文档其余部分一致）**

1. `cp env.docker.example .env`，填好 **`DATABASE_URL`**、**`MYSQL_DOCKER_NETWORK`**（如 `1panel-network`）。  
2. `mkdir -p data/uploads`  
3. `docker compose up -d`  

`docker-compose.yml` 中 `web` 已声明 **`image: business-mgm:latest`**，与本机构建出的镜像一致；若本地已有该 tag，**通常不会重复完整构建**（除非你加了 `--build` 或源码更新后需重建）。

**方式 B：直接 `docker run`（不经过 compose）**

```bash
docker run -d --name business-mgm-web --restart unless-stopped \
  -p 5000:5000 \
  -e FLASK_ENV=production \
  -e DATABASE_URL='mysql+pymysql://用户:密码@mysql:3306/business_mgm?charset=utf8mb4' \
  -e UPLOAD_DIR=/app/data/uploads \
  -v /home/xt/server/BUSINESS-MGM/data/uploads:/app/data/uploads \
  --network 1panel-network \
  business-mgm:latest
```

把 `用户:密码`、`1panel-network`、宿主机上传目录路径换成你的；密码含 `@` 需 URL 编码。

### 访问

- 移动端 H5：`http://服务器IP:5000/`  
- 管理后台：`http://服务器IP:5000/system-management`  
- 若前面有 Nginx/1Panel 反代 HTTPS，用域名访问即可。

### 把镜像迁到另一台服务器

在**当前机**导出：

```bash
docker save business-mgm:latest | gzip > business-mgm-latest.tar.gz
```

拷贝 `business-mgm-latest.tar.gz` 到目标机后：

```bash
gunzip -c business-mgm-latest.tar.gz | docker load
```

目标机仍需：**Docker**、**MySQL**（或连接现有库）、**相同方式**配置环境变量与 **`data/uploads` 卷**。镜像只包含应用与内置静态资源，**不包含**数据库里的数据与上传文件，需自行备份/迁移 MySQL 与 `data/uploads`。
