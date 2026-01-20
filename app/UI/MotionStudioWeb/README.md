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

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
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
