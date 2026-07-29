import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Comp/Card"
CardBase {
    id:root
    required property var alarmInfo
    required property var apiClient
    required property var style
    required property var authManager

    cardStyle: root.style
    cardAuthManager: root.authManager
    property string global_key: ""
    property bool showMore: false
    height: coll.height
    title: qsTr("报警综合")
    max_height:160
    content_body:Column{
        id:coll
        Layout.fillWidth: true
        width:parent.width
        AlarmItemSimpleView{
            alarmInfo: root.alarmInfo
        }

        }

    MouseArea{
        anchors.fill:parent
        acceptedButtons:Qt.RightButton
        onClicked:{
        menu.popup()
        }
    }
    Menu{
        id:menu
        MenuItem{
            text:"查看原始数据"
            onClicked:{
               Qt.openUrlExternally(root.apiClient.getLastUrlByKey("coilAlarm"))
            }
        }
    }

    }
