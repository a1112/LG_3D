# Rust Image Service

独立的高性能图像服务试验项目，用于替换或并行对比当前 Python 图像接口。

当前目标：

- 优先覆盖 `preview/source` 这类静态文件接口
- 兼容当前 `/image/area/{surface}/{coil}` 查询参数
- 优先读取预生成 tile 缓存，不做运行时整图切片
- 对 `defect_image` 建立 detection XML 索引缓存，避免每次遍历目录

当前已实现：

- `GET /health`
- `GET /image/preview/{surface_key}/{coil_id}/{type_}`
- `GET /image/source/{surface_key}/{coil_id}/{type_}`
- `GET /image/area/{surface_key}/{coil_id}`
  - `count=0` 返回宽高
  - `row=-2` 返回 preview
  - `row=-1` 返回原图
  - 其余走 `cache/area/tild/L{level}/{col}_{row}.jpg`
- `GET /defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}`

当前未实现：

- AREA tile 动态裁剪 fallback
- JPEG/WebP 运行时转码
- 3D Render / Error 图生成
- 与现有 FastAPI 的反向代理或灰度切流

运行方式：

```powershell
$env:PATH = \"$env:USERPROFILE\\.cargo\\bin;\" + $env:PATH
cd D:\\LCX_USER\\LG_3D\\app\\Server\\rust_image_service
cargo run --release -- --config D:\\CONFIG_3D\\configs\\Server3D.json --host 0.0.0.0 --port 6013
```

建议的下一步：

1. 先用 curl 或 QML 改端口，对比 `preview/source/area/meta/defect_image`
2. 如果 tile miss 仍频繁，再补运行时 tile fallback
3. 最后再迁移 `Render/Error` 这类 CPU 密集接口
