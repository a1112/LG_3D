import QtQuick
import QtQuick.Controls

Menu{
    id: root

    required property var modelStore
    required property var settings
    required property var appController
    required property var apiClient
    required property var coreController

    // 引用当前的缺陷项
    property var defectItem: null

    Menu{
        title:qsTr("纠正")
        MenuItem{
        }
    }

    MenuItem{
        text: qsTr("切换到图像")
        onClicked: {
            if (!defectItem) return

            // 获取缺陷信息
            let coilId = defectItem.coilId
            let surface = defectItem.surface  // "S" 或 "L"

            console.log("切换到图像 - coilId:", coilId, "surface:", surface)

            // 在卷材列表中查找对应的卷材
            let found = false
            let targetCoil = null

            // 先在当前列表中查找
            for (let i = 0; i < root.modelStore.currentCoilListModel.count; i++) {
                let coil = root.modelStore.currentCoilListModel.get(i)
                if (coil && Number(coil.Id) === Number(coilId)) {
                    targetCoil = coil
                    found = true
                    break
                }
            }

            // 如果当前列表中没有，在完整列表中查找
            if (!found) {
                for (let i = 0; i < root.modelStore.realCoilListModel.count; i++) {
                    let coil = root.modelStore.realCoilListModel.get(i)
                    if (coil && Number(coil.Id) === Number(coilId)) {
                        targetCoil = coil
                        found = true
                        break
                    }
                }
            }

            if (!found || !targetCoil) {
                console.log("未找到对应的卷材:", coilId)
                return
            }

            // 设置当前卷材
            root.coreController.currentCoilModel.init(targetCoil)

            // 切换到数据显示页面
            root.appController.appIndex = 0  // 切换到数据显示页面

            // 设置对应的表面
            let surfaceData = surface === "S" ? root.modelStore.surfaceS : root.modelStore.surfaceL
            surfaceData.rootViewto2D()  // 切换到2D视图

            // 保存缺陷位置信息到 CoreModel，供 DataShowCore 使用
            // 延迟设置，确保页面切换完成
            Qt.callLater(function() {
                root.modelStore.pendingDefect = {
                    defect_x: defectItem.defectX,
                    defect_y: defectItem.defectY,
                    defect_w: defectItem.defectW,
                    defect_h: defectItem.defectH,
                    coilId: coilId,
                    surface: surface,
                    viewMode: "2D"
                }
            })
        }
    }

    MenuItem{
        text: qsTr("打开图像位置")
        onClicked: {
            if (!root.defectItem) return

            let coilId = root.defectItem.coilId
            let surface = root.defectItem.surface  // "S" 或 "L"

            // 获取文件夹路径
            let folderPath = ""
            let targetSurfaceData = surface === "S" ? root.modelStore.surfaceS : root.modelStore.surfaceL

            if (targetSurfaceData.serverIsLocal) {
                // 本地服务器：使用本地路径
                folderPath = targetSurfaceData.getBaseUrl(coilId)
            } else {
                // 远程服务器：使用共享文件夹路径
                let sharedFolderBase = "\\\\\\\\" + root.apiClient.apiConfig.hostname
                                     + "/" + root.settings.sharedFolderBaseName
                folderPath = sharedFolderBase + surface + "/" + coilId
            }

            console.log("打开文件夹:", folderPath)

            // 打开文件夹 (folderPath 已经包含 file:/// 前缀或需要转换)
            if (folderPath.startsWith("file:///")) {
                Qt.openUrlExternally(folderPath)
            } else {
                Qt.openUrlExternally("file:///" + folderPath)
            }
        }
    }

}
