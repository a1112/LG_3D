# Rust Image Service

独立的高性能图像服务试验项目，用于替换或并行对比当前 Python 图像接口。

当前目标：

- 优先覆盖 `preview/source` 这类静态文件接口
- 兼容当前 `/image/area/{surface}/{coil}` 查询参数
- 优先读取预生成 tile 缓存，并在缓存缺失时提供 Python 兼容的运行时切片 fallback
- 对 `defect_image` 建立 detection XML 索引缓存，避免每次遍历目录

当前已实现：

- `GET /health`
- `GET /image/preview/{surface_key}/{coil_id}/{type_}`
- `GET /image/source/{surface_key}/{coil_id}/{type_}`
- `GET /coilData/Render/{surface_key}/{coil_id}`
  - `thumbnail=true` 时读取 `cache/falsecolor/{gray|jet}/thumbnail_1024.jpg`
  - 返回与主 Rust API 兼容的 `X-Thumbnail` / `X-Colormap` / `X-From-Cache` 头
- `GET /coilData/Error/{surface_key}/{coil_id}`
  - `png/Error.png` 与 `Error.json` 阈值元数据匹配时读取缓存
  - 缓存缺失、阈值不匹配或 `force_cache=true` 时返回主 Rust API 兼容的 100x100 透明 PNG
- `GET /image/area/{surface_key}/{coil_id}`
  - `count=0` 返回宽高
  - `row=-2` 返回 preview
  - `row=-1` 返回原图
  - `row`、`col`、`count`、`level` 查询参数按 FastAPI/Python 范围返回兼容的 `422` JSON
  - 其余优先走 `cache/area/tild/L{level}/{col}_{row}.jpg`，miss 时按 Python 主服务 fallback 规则切片
- `GET /defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}`
- `testMode` / `testDataDir` / `testDataCoilId` 配置字段，以及 `D:\CONFIG_3D\test_mode_config.json` 的测试模式开关

当前未实现：

- JPEG/WebP 运行时转码
- `Render` / `Error` 缓存缺失时的动态深度图生成
- 与现有 FastAPI 的反向代理或灰度切流

运行方式：

```powershell
$env:PATH = \"$env:USERPROFILE\\.cargo\\bin;\" + $env:PATH
cd D:\\LCX_USER\\LG_3D\\app\\Server\\rust_image_service
cargo run --release -- --config D:\\CONFIG_3D\\configs\\Server3D.json --host 0.0.0.0 --port 6013
```

建议的下一步：

1. 先用 curl 或 QML 改端口，对比 `preview/source/area/meta/defect_image`
2. 继续对比生产 `preview/source/area/meta/defect_image` 样本
3. 迁移 `Render/Error` 缓存缺失时的动态深度图生成
