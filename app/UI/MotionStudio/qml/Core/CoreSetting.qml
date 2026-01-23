import QtQuick
import "../Base"

Item {

    id:root

    property bool useSharedFolder: false
    property string sharedFolderBaseName: "Save_"

    property bool useImageCache: false
    property int maxImageCache: 15


    property string server_ip: "127.0.0.1"
    property int server_port: 5010
    property int server_port_count: 1

    property int databasPort: 6011
    property int imageServerPort: 6012
    property int dataPort: 6013
    property int plcPort: 6014

    property int updataTime: 8000

    // 保持最新图像 -> 时间
    property int autoKeepTimeMax: 180

    property bool useLoc: false

    // AREA 视图初始分块（每边块数），加载完尺寸后会按需调整
    property int defaultAreaTileCount: 3

    property string clipModeS: "fixed"
    property int clipFixedValueS: 200
    property real clipDynamicAS: 3.0
    property real clipDynamicBS: 220.0
    property real clipDynamicCS: 2600.0

    property string clipModeL: "fixed"
    property int clipFixedValueL: 200
    property real clipDynamicAL: 3.0
    property real clipDynamicBL: 220.0
    property real clipDynamicCL: 4000.0

property int alg2dPort: 6020

property bool testMode: false

property bool showErrorOverlay: true  // 是否显示错误叠加层（3D Error 图像）

property int headDateShowModel: 0
    property int dataHeaderHeight:320
    SettingsBase{
        property alias useImageCache: root.useImageCache
        property alias maxImageCache: root.maxImageCache
        property alias useSharedFolder: root.useSharedFolder
        // property alias updataTime: root.updataTime
        property alias autoKeepTimeMax: root.autoKeepTimeMax
        property alias useLoc: root.useLoc
        property alias sharedFolderBaseName: root.sharedFolderBaseName

        property alias server_ip: root.server_ip
        property alias server_port: root.server_port
        property alias server_port_count: root.server_port_count
        property alias databasPort: root.databasPort
        property alias imageServerPort: root.imageServerPort
        property alias dataPort: root.dataPort
        property alias plcPort: root.plcPort

        property alias headDateShowModel:root.headDateShowModel
        property alias dataHeaderHeight:root.dataHeaderHeight
        property alias defaultAreaTileCount: root.defaultAreaTileCount
        property alias clipModeS: root.clipModeS
        property alias clipFixedValueS: root.clipFixedValueS
        property alias clipDynamicAS: root.clipDynamicAS
        property alias clipDynamicBS: root.clipDynamicBS
        property alias clipDynamicCS: root.clipDynamicCS

        property alias clipModeL: root.clipModeL
        property alias clipFixedValueL: root.clipFixedValueL
        property alias clipDynamicAL: root.clipDynamicAL
        property alias clipDynamicBL: root.clipDynamicBL
        property alias clipDynamicCL: root.clipDynamicCL

property alias alg2dPort: root.alg2dPort
property alias testMode: root.testMode
property alias showErrorOverlay: root.showErrorOverlay
category: "AppSettings"
        location: "settings.ini"
    }
}
