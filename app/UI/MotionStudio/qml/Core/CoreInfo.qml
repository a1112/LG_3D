import QtQuick

Item {
    id: root

    // 原始图像保存位置（S/L）
    property string originalImageFolderS: ""
    property string originalImageFolderL: ""

    // 处理/保存后图像位置（S/L）
    property string saveImageFolderS: ""
    property string saveImageFolderL: ""

    // 运行环境
    property string pythonVersion: ""
    property string cacheMode: ""
    property string cpuModel: ""
    // 多个 GPU 用换行拼接
    property string gpuModels: ""

    // 服务器版本（配置中的 VERSION）
    property string serverVersion: ""

    // 数据库连接信息
    property string databaseUrl: ""
}
