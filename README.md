# LG_3D

## Rust/Tauri 本地开发端口

- React/Vite UI: `http://127.0.0.1:3015`
- Rust API: `http://127.0.0.1:5011`
- Rust image service: `http://127.0.0.1:6013`

当前 Rust-only 开发栈不占用 Python/QML 参考端口 `5010`、`6001`、`6005`，避免和本机已有服务冲突。

## Rust + 前端一致性核验

```bash
# API 路由（Python 装饰器）与 Rust 路由对账
python scripts/verify_rust_api_parity.py

# 进一步检查 MotionStudioWeb 的前端服务路径是否全部在 Rust 中具备
python scripts/verify_rust_api_parity.py --frontend
```

## Rust API + Rust Image + Tauri/Web 一键启动

```bash
# 先配置数据库连接（脚本启动会读取当前用户环境变量）
setx COIL_DATABASE_URL "mysql://user:pass@127.0.0.1:3306/Coil"

# 在仓库根目录运行（含 Web + API + Image）
pwsh .\\scripts\\start_rust_motion_studio_dev.ps1

# 可选：指定 image_service 的配置文件
pwsh .\\scripts\\start_rust_motion_studio_dev.ps1 -ImageConfigPath "D:\\CONFIG_3D\\configs\\Server3D.json"
```


https://peps.python.org/pep-0008/

pip config --global set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config --global set install.trusted-host mirrors.aliyun.com

python -m pip install --upgrade pip

pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu126

https://github.com/tporadowski/redis/releases

git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy https://127.0.0.1:7890
