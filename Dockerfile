# 多阶段：先构建 Vue 管理端与移动端，再安装 Python 依赖并复制后端代码。
#
# NODE_IMAGE / PYTHON_IMAGE 必须写在**第一个 FROM 之前**，否则旧版 docker build 在第二段 FROM 时
# 会得到空变量（报错: base name (${PYTHON_IMAGE}) should not be blank）。
#
# 若能直连 Docker Hub，构建时传入:
#   --build-arg NODE_IMAGE=node:20-alpine --build-arg PYTHON_IMAGE=python:3.12-slim-bookworm ...

ARG NODE_IMAGE=docker.m.daocloud.io/library/node:20-alpine
ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim-bookworm

FROM ${NODE_IMAGE} AS frontend
WORKDIR /src
COPY frontend-admin ./frontend-admin
COPY frontend-mobile ./frontend-mobile
COPY backend ./backend

ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN if [ -n "${NPM_REGISTRY}" ]; then npm config set registry "${NPM_REGISTRY}"; fi \
    && cd frontend-admin && npm ci && npm run build \
    && cd ../frontend-mobile && npm ci && npm run build

FROM ${PYTHON_IMAGE}
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -i "${PIP_INDEX_URL}" -r requirements.txt

COPY --from=frontend /src/backend /app

EXPOSE 5000
CMD ["python", "run_server.py"]
