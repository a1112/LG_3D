import QtQuick
import "./Base"
Item {
    id:root
    property int appIndex : 0   // 对于 主界面显示界面
    SettingsBase{
        property alias appIndex: root.appIndex
        category:"app_root"
    }
}
