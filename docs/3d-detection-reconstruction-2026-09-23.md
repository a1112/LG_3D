# 3D 检测与模型重建实现记录

日期：2026-09-23。项目：`D:\LCX_USER\LG_3D`。

## 实现范围

本次完成现有端面深度数据的检测、判级、保存、三角网格重建、API 可用性判断和桌面显示链路修复。未修改现场标定参数或重启生产服务。

处理链路为：相机数据与标定 → 拼接深度/掩膜 → 轮廓、塔形、松卷及图像缺陷检测 → 按配置判级与保存 → 异步生成 OBJ/Qt 网格 → API/桌面刷新。

## 检测与结果保存

| 问题 | 修复后的行为 |
| --- | --- |
| 无效深度、负数、NaN/Inf 污染基准高度 | 深度输入验证，掩膜外和无效值归零；基准只使用有效前景；整数点数组转毫米前先转换为浮点 |
| 拼接旋转 90° 后 X/Y 标定仍使用原轴 | 奇数次四分之一圈旋转同步交换 X/Y 比例，保存元数据与图像坐标一致 |
| 容器迭代被上一个阶段或异常消耗 | 单端面和多端面容器均支持独立、嵌套迭代；一个端面失败不再跳过另一个端面 |
| 检测分块漏掉余数边界或小图 | 分块覆盖完整图像，并保留重叠区；小图至少产生一个有效块 |
| 分块检测坐标重复/遗漏偏移 | 直接检测模式添加一次块原点，检测加分类模式保留已有全局坐标；训练 XML 转回局部坐标 |
| 缺陷合并消耗原始结果，综合等级未包含缺陷 | 合并使用副本；按共享类别等级与显示开关判级，计入综合等级；无结果与无缺陷分开处理 |
| 扁卷/松卷运行配置被测试字典覆盖 | 使用配置中的默认项及去向覆盖，并校验有效阈值 |
| 实心掩膜被恢复出不存在的内孔 | 轮廓及径向恢复均要求真实孔洞/背景到前景边界；无法检测时保存处理错误 |
| 扁卷内径仅乘 X 比例，忽略旋转及各向异性 | 对椭圆应用 X/Y 标定，利用奇异值取得毫米短轴；在已有 JSON 字段保存内径和椭圆角度，无需数据库迁移 |
| 松卷输出固定宽度或混用像素/毫米 | 使用各方向真实缺测段长度，按方向标定换算；保存毫米单位标记，避免 API 再次缩放 |
| 保存或判级失败仅写日志 | 每端面返回处理错误集合，继续其他端面；协调器更新钢卷状态、消息及手动重检错误 |
| 界面使用旧公式和固定阈值重算新结果 | Web/QML 优先显示已保存的标定内径、角度和等级，历史数据保留兼容回退 |
| 报表导出硬编码标定系数 | 新记录使用保存的毫米内径，历史内外径按各自记录的 X 标定换算；只有缺失标定时使用历史默认值 |

正常测量得到超限值会产生产品报警；无有效数据、算法异常或写库失败会产生处理错误。两者在代码中分别记录。

关键文件：`app/Base/alg/detection.py`、`app/Base/property/Base.py`、`app/Base/property/Data3D.py`、`app/algorithm_runtime/AlarmDetection/`、`app/algorithm_runtime/SplicingService/`。

## 重建与显示

网格坐标单位统一为毫米：X 使用列坐标及 X 标定，Y 使用行坐标及 Y 标定，Z 使用 `raw * scale_z + offset_z - baseline_mm`。降采样保留原始步长及内圈中心，不再因缺测区域改变参考中心。

滤波仅使用有效深度，原始孔洞不会被当作零高度测量或被补成网格。三角面同时检查顶点、跨度和采样格之间的原始有效性，因此未落到采样点上的小孔也不会被跨接。删除无效/退化三角面及孤立顶点，并保持一致的正面法向。

OBJ 先写同目录临时文件再原子替换。构建失败保留上次模型，通过 `mesh_status.json` 发布 `processing / ready / error`。Balsam 转换失败时有效 OBJ 仍可显示；模型队列及停止流程有超时边界。

桌面通过 OBJ 的 RuntimeLoader 和原生 `.mesh` 的 Model 分别加载。Qt RuntimeLoader 支持 OBJ/glTF，Qt 原生网格由 Model 加载，因此不能把 `.mesh` 当作 RuntimeLoader 输入。依据：[Qt 6.8 RuntimeLoader](https://doc.qt.io/qt-6.8/qml-qtquick3d-assetutils-runtimeloader.html)、[Qt 6.8 Model](https://doc.qt.io/qt-6.8/qml-qtquick3d-model.html)。

生产可用性判断支持根目录 `3D.obj` 或 `meshes/defaultobject_mesh.mesh`，Python/Rust 一致。桌面优先读取新 OBJ，通过文件时间戳与大小检测同路径重写，重检结束重新请求数据。界面显示重建过程和失败状态。

修复了两个格式的背面剔除和旋转中心偏移。两份模型在父坐标系沿 X 轴排列，镜头等待真实边界有效后按视口比例、视场角和当前尺度完成初始取景，切换/重建后重新适配。进入 3D 视图会立即刷新文件，当前 3D 视图和仍在处理的任务继续轮询。

双面视图显示同一实测端面的正面与背面；它不是两端面的空间配准，也未补造未采集的侧壁或完整闭合钢卷实体。

关键文件：`app/algorithm_runtime/Save3D/save.py`、`app/Server/testdata_mesh.py`、`app/UI/MotionStudio/qml/DataShow/View3D/`、`app/UI/MotionStudio/qml/Core/Surface/SurfaceData.qml`。

## 离线验证

合成数据经真实 Open3D 重建、OBJ 导出、Balsam 转换及生产 QML 组件渲染验证。数据库、PLC 和相机硬件未参与该验证。

| 项目 | 实测结果 |
| --- | --- |
| 有效深度像素 | 111,273 |
| 网格顶点 / 三角面 | 12,363 / 23,860 |
| 尺寸 | 258.00 × 258.75 × 15.47228 mm |
| 中心孔 / 局部缺测孔跨接三角面 | 0 / 0 |
| 相对合成解析曲面的最大高度误差 | 0.06545 mm 以内 |
| OBJ 写入/读回最大高度误差 | 0.000006 mm 以内 |
| Qt 原生网格转换 | 成功 |
| OBJ / `.mesh` 真实渲染 | 均加载成功、边界尺寸有效；离屏 OpenGL，无可见桌面窗口 |

上述误差属于合成算例的数值验证，不代表现场设备精度或缺陷检出率。

完整结果：`work/3d_implementation_20260923/synthetic/verification.json`。仓库附带离屏验证脚本及部分预览图；大体积模型由验证脚本在同一工作目录生成。

复跑重建：

```powershell
.venv/Scripts/python.exe scripts/verify_3d_reconstruction.py
```

复跑生产 QML 单模型离屏验证：

```powershell
.venv/Scripts/python.exe work/3d_implementation_20260923/preview_qml.py work/3d_implementation_20260923/synthetic/3D.obj work/3d_implementation_20260923/obj_preview.png
.venv/Scripts/python.exe work/3d_implementation_20260923/preview_qml.py work/3d_implementation_20260923/synthetic/meshes/defaultobject_mesh.mesh work/3d_implementation_20260923/mesh_back_preview.png 180
```

## 回归验证

| 检查 | 原工作区完整结果 |
| --- | --- |
| Python 项目回归及 ServiceMonitor | 837 通过，2 跳过 |
| Web Vitest | 70 个测试文件，743 项通过 |
| Web ESLint | 通过 |
| Web TypeScript + Vite 构建 | 通过；既有单包体积提示仍存在 |
| Rust API | 13 个库测试、4 个主程序测试、326 个路由测试，共 343 项通过 |
| Ruff 严重错误 F821/F822/F823/E9 | 通过 |
| Git diff 空白检查 | 通过 |
| Open3D → OBJ → Balsam → Qt | 真实离线执行通过 |

以上完整结果来自包含其他既有修改的原工作区，日志保存在该工作区的 `work/3d_implementation_20260923/`，没有纳入本次提交。Python 跳过的两项明确需要缺失的本地原始采集数据集。

只包含本次 3D 相关文件的独立提交快照另外执行了完整回归：Python 753 项通过、2 项跳过；Web 的 3D 定向测试 15 项通过，TypeScript/Vite 构建通过；Rust 路由 324 项通过、2 项摄像头行为测试失败；Web 完整测试 646 项通过、24 项失败、61 项跳过，失败集中在未纳入本次提交的既有 QML 行为与测试。该快照的 3D Python 定向测试 106 项通过。摄像头与 QML 的完整回归仍需在后续集成中修复。

Qt 单组件验证覆盖 OBJ 与原生网格正面、背面、45° 旋转叠加非均匀缩放及平移，共六种场景。背面修复前有效几何像素为 0，修复后为 39,353；组合变换后的中心与目标平移一致。详见 `render_verification.json`。

整页生产 `View3DRoot` 另验证 OBJ 原比例、2 倍、8 倍及原生网格四种场景，左右模型均完整可见。8 倍场景的显示直径约 2,070 mm，相机自动调整到约 3,040.18 mm，未裁切模型；验证脚本为 `preview_viewer_qml.py`，截图和参数为 `viewer_scale8.png/json`。最后的 QML 与接口相关 Python 子集复验 81 项通过，不重复计入全量数量。

新增行为回归覆盖：无效深度、基准和坐标换算、旋转标定、分块及 XML 坐标、缺陷等级、各端面隔离、保存异常、真实环形几何、网格孔洞、OBJ 原子替换、工作队列退出、测试数据缓存、重检消息、Web/QML 标定内径和 Rust API 字段透传。

## 适用边界

- 本机缺少原始采集测试集，相关两项测试跳过；真实钢卷、现场相机/PLC、GPU 权重推理精度和生产吞吐需在现场验证。
- 塔形沿用现有径向 LINE 算法。AREA/POINT/WK 缺少可执行的业务判定规范，仍明确警告并使用既有 LINE 回退，没有编造新的判级规则。
- 保留既有深度相对高度范围及三角面跨度限制，未擅自改变现场工艺阈值。
- 本次为源码及离线验证交付。生效涉及算法进程、Python API（或 Rust API）、MotionStudio 桌面包与 Web 构建；未进行生产部署。
