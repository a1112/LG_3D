import QtQuick
import Qt.labs.settings
Item {

    id:root

    property bool useSharedFolder: true
    property string sharedFolderBaseName: "Save_"

    property bool useImageCache: false
    property int maxImageCache: 15


    property string server_ip: "127.0.0.1"
    property int server_port: 6010

    property int databasPort: 6011
    property int imageServerPort: 6012
    property int dataPort: 6013
    property int plcPort: 6014

    property int updataTime: 300

    // 保持最新图像 -> 时间
    property int autoKeepTimeMax: 180

    property bool useLoc: false

    Settings{
        property alias useImageCache: root.useImageCache
        property alias maxImageCache: root.maxImageCache
        property alias useSharedFolder: root.useSharedFolder
        property alias updataTime: root.updataTime
        property alias autoKeepTimeMax: root.autoKeepTimeMax
        property alias useLoc: root.useLoc
        property alias sharedFolderBaseName: root.sharedFolderBaseName

        property alias server_ip: root.server_ip
        property alias server_port: root.server_port
        property alias databasPort: root.databasPort
        property alias imageServerPort: root.imageServerPort
        property alias dataPort: root.dataPort
        property alias plcPort: root.plcPort

        category: "AppSettings"
        fileName: "settings.ini"
    }
}
