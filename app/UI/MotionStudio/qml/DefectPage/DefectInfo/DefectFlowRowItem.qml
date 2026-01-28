import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../btns"
import "../../Model/server"
Item {
    height: 25

    // 直接使用 model 数据
    property string defectName: model.name || ""
    property int defectLevel: model.level || 0
    property color defectColor: model.color || "#00000000"
    property bool defectShow: model.show !== undefined ? model.show : false
    property bool filterShow: model.filter !== undefined ? model.filter : true
    property int defectNum: model.num !== undefined ? model.num : 0

    // 布局：名称（数量）选择框
    RowLayout {
        id: rowLayout
        anchors.fill: parent
        spacing: 4

        // 名称
        Label {
            text: defectName
            font.pointSize: 12
            color: filterShow ? defectColor : (coreStyle.isDarkTheme ? "#FFFFFF" : "#000000")
            font.bold: true
            Layout.alignment: Qt.AlignVCenter
        }

        // 数量
        Label {
            text: "(" + defectNum + ")"
            font.pointSize: 11
            color: filterShow ? defectColor : (coreStyle.isDarkTheme ? "#AAAAAA" : "#666666")
            Layout.alignment: Qt.AlignVCenter
        }

        // 选择框
        Item {
            Layout.preferredWidth: 40
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignVCenter

            CheckBox {
                anchors.centerIn: parent
                checked: filterShow
                onCheckedChanged: {
                    model.filter = checked
                    defectViewCore.filterCore.resetFilterDict()
                }
                Material.accent: defectColor
            }
        }
    }

    visible: defectShow || (!defectShow && defectViewCore.filterCore.fliterShowBgDefect)
}
