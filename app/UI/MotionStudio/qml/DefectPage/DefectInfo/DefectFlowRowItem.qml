pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: root
    height: 25
    required property var model
    required property var style
    required property var viewController

    // 直接使用 model 数据
    property string defectName: root.model.name || ""
    property int defectLevel: root.model.level || 0
    property color defectColor: root.model.color || "#00000000"
    property bool defectShow: root.model.show !== undefined ? root.model.show : false
    property bool filterShow: root.model.filter !== undefined ? root.model.filter : true
    property int defectNum: root.model.num !== undefined ? root.model.num : 0

    // 布局：名称（数量）选择框
    RowLayout {
        id: rowLayout
        anchors.fill: parent
        spacing: 4

        // 名称
        Label {
            text: root.defectName
            font.pointSize: 12
            color: root.filterShow ? root.defectColor : root.style.textColor
            font.bold: true
            Layout.alignment: Qt.AlignVCenter
        }

        // 数量
        Label {
            text: "(" + root.defectNum + ")"
            font.pointSize: 11
            color: root.filterShow ? root.defectColor : root.style.secondaryTextColor
            Layout.alignment: Qt.AlignVCenter
        }

        // 选择框
        Item {
            Layout.preferredWidth: 40
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignVCenter

            CheckBox {
                anchors.centerIn: parent
                checked: root.filterShow
                onCheckedChanged: {
                    root.model.filter = checked
                    root.viewController.filterCore.resetFilterDict()
                }
                Material.accent: root.defectColor
            }
        }
    }

    visible: root.defectShow
             || (!root.defectShow && root.viewController.filterCore.fliterShowBgDefect)
}
