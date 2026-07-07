# Motion Studio Web

3D卷材端面检测系统 - Web版本

## 技术栈

- **构建工具**: Vite
- **前端框架**: React 18 + TypeScript
- **3D渲染**: React Three Fiber + Three.js
- **状态管理**: Zustand
- **数据请求**: React Query + Axios
- **UI组件**: Ant Design
- **图表**: Recharts
- **路由**: React Router

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 启动 Rust API + Rust Image + Web 的一键联调脚本（项目根目录执行）
pwsh ..\\..\\..\\scripts\\start_rust_motion_studio_dev.ps1

# 可选：指定非默认 image_service 配置文件
#   -ImageConfigPath "C:\\configs\\Server3D.json"
# 或设置环境变量 RUST_IMAGE_CONFIG

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 与 Rust API 一致性校验

```bash
# 仅校验前端服务调用是否覆盖到 Rust 路由
python ../../../scripts/verify_rust_api_parity.py --frontend

# 同时校验 Python 路由与 Rust 路由（建议每次回归前执行）
python ../../../scripts/verify_rust_api_parity.py --json

# 或直接使用 npm 脚本（项目根为 app/UI/MotionStudioWeb）
npm run parity:api
```

## 项目结构

```
src/
├── components/       # 通用组件
├── pages/           # 页面组件
│   ├── DataShow/   # 数据展示页面
│   └── DefectShow/ # 缺陷展示页面
├── services/        # API服务
├── stores/          # 状态管理
├── types/           # TypeScript类型定义
├── utils/           # 工具函数
├── App.tsx          # 主应用组件
└── main.tsx         # 应用入口
```

## 与QML版本的关系

- Web版本与QML版本共用同一个FastAPI后端服务
- 两个版本可以独立运行，互不影响
- 后端API服务位于 `app/Server/api/`
