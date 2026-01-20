# 部署说明

## 开发环境

```bash
# 安装依赖
npm install

# 启动开发服务器（默认端口 3000）
npm run dev
```

开发服务器会自动代理 API 请求到 FastAPI 后端（http://localhost:8000）

## 生产构建

```bash
# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

构建产物位于 `dist` 目录。

## 与 QML 版本共存

两个版本共用同一个 FastAPI 后端服务：

- **QML 版本**: `app/UI/MotionStudio/`
- **Web 版本**: `app/UI/MotionStudioWeb/`

### 后端配置

后端服务需要配置 CORS 以允许 Web 版本访问：

```python
# 在 FastAPI 应用中添加 CORS 中间件
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Web 开发服务器地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 部署选项

1. **独立部署**:
   - Web 版本构建后部署到独立的 Web 服务器
   - QML 版本作为桌面应用独立运行

2. **集成部署**:
   - Web 版本可以嵌入到 QML 应用中（使用 WebEngineView）
   - 两个版本共享后端 API 服务

## 注意事项

1. 确保 FastAPI 后端服务正在运行
2. 检查 API 端点路径是否匹配
3. 验证 CORS 配置是否正确
4. 根据实际数据格式调整 3D 数据解析逻辑（见 `src/utils/dataParser.ts`）
