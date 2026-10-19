# Canvas3D 资源归属与合成回归

点云 effect 为当前数据创建并挂接一个 Points，负责在替换或卸载时移除它，并释放自己创建的几何体和材质。相同数据只改变 Z 缩放时继续复用资源。材质参数、点云坐标和颜色计算保持原有行为。

数据源 effect 只保留当前输入的一个待解析动画帧。输入替换或卸载时取消旧帧，并将该代标记为退役；即使旧回调随后被调度，也不会解析旧数据或写回状态。每个光栅图像 URL 由创建它的 effect 直接释放，清理不依赖可变的 React 图像状态，也不在卸载时更新状态。

在 `app/UI/MotionStudioWeb` 运行：

```sh
node --test --test-reporter=tap scripts/canvas3d-lifecycle.node.cjs
node node_modules/vitest/vitest.mjs run src/components/Canvas3D/utils.test.ts src/utils/dataParser.test.ts --maxWorkers=1 --no-file-parallelism
node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
node node_modules/vite/bin/vite.js build
```

生命周期脚本转译实际组件源码，仅为测试路由增加私有 PointCloud 导出，不修改产品导出。它使用受控 hooks、ref、host、动画帧和 URL 注册表，并调用真实 Three.js CPU 几何体、材质与数据解析函数。导入白名单阻止加载应用服务或状态初始化；没有 fetch、WebSocket、相机、设备或采集入口。

原始代码的 12 项专项中有 9 项失败：40 次点云替换留下 40 个未收到 dispose 的材质，卸载后末次几何体仍未释放；40 次二进制输入替换留下 40 个待执行帧，迟到帧能覆盖当前回退点云。修复后活动资源各保留一份、待解析帧最多一份，卸载后归零。其他用例保留当前二进制解析、Z 缩放、回退数据和图像 URL 归属的活动对照。

这是受控模型中的 effect 与 API 调用证据。effect 回放并非真实 React StrictMode 挂载验收，URL 和文件头用例并非图像解码或显示验收；dispose 事件计数也不代表 GPU 或整应用 RAM 已回收。未挂载 ReactDOM、R3F、WebGL 或原生窗口，未运行 Qt、Rust/Python 服务、工业采集或硬件检测。整应用 RAM 配对和原生拖拽/缩放验收仍为未测。
