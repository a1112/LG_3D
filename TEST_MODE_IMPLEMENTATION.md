# 测试模式功能实现文档

## 功能概述

实现了完整的测试模式功能，包括UI设置界面、后端API、数据源切换和系统信息展示。测试模式下系统使用 TestData 目录的固定数据，避免影响生产环境。

## 实现的功能

### 1. 设置界面 - 其他选项
- **文件位置**: `app/UI/MotionStudio/qml/SettingPage/OtherSetting/OtherSetting.qml`
- **功能**: 添加了测试模式开关控件，用户可以通过UI直接切换测试模式

### 2. 设置界面 - 信息页面
- **文件位置**: `app/UI/MotionStudio/qml/SettingPage/InfoSetting/InfoSetting.qml`
- **功能**: 显示系统运行信息，包括：
  - 数据源目录（测试模式显示 TestData/125143，生产模式显示实际数据源）
  - 存储目录信息
  - 运行模式状态指示器（测试模式红色，生产模式绿色）
  - 主机名、数据库状态、API端口等信息
  - 刷新按钮功能

### 3. 后端API
- **文件位置**: `app/Server/api/ApiSettings.py`
- **新增API端点**:
  - `GET /settings/test_mode` - 获取测试模式状态
  - `POST /settings/test_mode` - 设置测试模式状态
  - `GET /settings/test_mode_status` - 获取详细状态信息

### 4. 配置管理
- **配置文件**: `CONFIG_3D/test_mode_config.json`（已添加到.gitignore）
- **配置属性**: 在 `app/UI/MotionStudio/qml/Core/CoreSetting.qml` 中添加 `testMode` 属性

### 5. 系统配置合并
- **文件位置**: `app/Base/CONFIG.py`
- **修改内容**: 
  - 将 `developer_mode` 和 `isLoc` 合并为统一的 `developer_mode` 设置
  - 本地开发环境自动启用测试模式
  - 保留 `isLoc` 变量以兼容现有代码

### 6. 缓存逻辑更新
- **文件位置**: `app/Server/cache/base.py`
- **修改内容**: 简化条件判断，使用统一的 `developer_mode`

### 7. 界面标题显示
- **文件位置**: `app/UI/MotionStudio/qml/App.qml`
- **功能**: 在测试模式下标题栏显示"[测试模式]"标识

### 8. 设置页面更新
- **文件位置**: `app/UI/MotionStudio/qml/SettingPage/SettingPageView.qml`
- **修改内容**: 
  - 在标签栏添加了"信息"页面
  - 将信息页面插入到3D渲染设置和其他设置之间

## QRC 资源文件更新

- **文件位置**: `app/UI/MotionStudio/qml.qrc`
- **新增条目**: 
  ```
  <file>qml/SettingPage/InfoSetting/InfoSetting.qml</file>
  ```
- **行号**: 566

## 测试模式特性

### 数据来源
- **测试数据目录**: `TestData/125143/`
- **固定测试卷ID**: `125143`
- **数据映射规则**:
  - 3D数据: 任何请求的3D文件映射到 `TestData/125143/3D.npz`
  - 图像数据: 按类型映射到对应子目录（png/, jpg/, mask/等）
  - 预览图: 映射到 `TestData/125143/preview/`

### 持久化存储
- **配置文件**: `CONFIG_3D/test_mode_config.json`
- **Git忽略**: 已添加到 `.gitignore`，不被版本控制跟踪
- **运行时同步**: API调用时同时更新 `CONFIG.developer_mode` 和 `CONFIG.isLoc`

### 视觉反馈
- **标题栏**: 测试模式下显示"[测试模式]"后缀
- **信息页面**: 彩色状态指示器（红色=测试模式，绿色=生产模式）
- **设置界面**: 直观的开关控件

## 使用方法

### 开启测试模式
1. **UI设置**: 设置 → 其他 → 测试模式（开关）
2. **环境变量**: `set API_DEVELOPER_MODE=true`
3. **配置文件**: 在 `CONFIG_3D` 目录下创建 `developer_mode=true` 文件
4. **自动检测**: 本地开发环境（特定主机名）自动启用

### 查看系统信息
1. 打开设置界面
2. 点击"信息"标签页
3. 查看数据源、存储目录、运行模式等信息
4. 可点击"刷新信息"按钮更新状态

## 兼容性说明

- **向后兼容**: 保留了 `isLoc` 变量以支持现有代码
- **配置同步**: UI设置会同时更新 `developer_mode` 和 `isLoc` 两个变量
- **缓存逻辑**: 简化了判断条件，但保持功能不变

## 注意事项

1. **测试数据**: 确保 `TestData/125143/` 目录存在且包含必要的测试数据文件
2. **配置文件**: `test_mode_config.json` 已加入 `.gitignore`，不会被提交到版本控制
3. **重启生效**: 某些设置可能需要重启服务才能完全生效
4. **开发环境**: 特定主机名的开发环境会自动启用测试模式

## 文件修改清单

### 新增文件
- `app/UI/MotionStudio/qml/SettingPage/InfoSetting/InfoSetting.qml`

### 修改文件
- `app/UI/MotionStudio/qml/SettingPage/OtherSetting/OtherSetting.qml`
- `app/UI/MotionStudio/qml/Core/CoreSetting.qml`
- `app/Server/api/ApiSettings.py`
- `app/Base/CONFIG.py`
- `app/Server/cache/base.py`
- `app/UI/MotionStudio/qml/App.qml`
- `app/UI/MotionStudio/qml/SettingPage/SettingPageView.qml`
- `app/UI/MotionStudio/qml/Core/Core.qml`
- `app/UI/MotionStudio/qml.qrc`
- `.gitignore`

所有功能已完成实现并集成到系统中，用户现在可以通过设置界面轻松管理测试模式，并查看详细的系统运行状态信息。