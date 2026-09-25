import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../Comp/Card"
CardBase {
    id: root

    required property var viewController
    required property var style
    required property var authManager

    cardStyle: root.style
    cardAuthManager: root.authManager

    readonly property var defectModel: root.viewController.defectCoreModel

    Layout.fillWidth: true
    max_height: 100
    title: qsTr("缺陷概览")

    content_body:Item{
        id:col
        width:root.width
        Layout.fillWidth: true
        Layout.fillHeight: true
                visible: root.isShow
        Flow{
            anchors.fill: parent
            Layout.fillWidth: true
            Layout.fillHeight: true

            FlowRowItem{
                title:qsTr("缺陷数量")
                value: root.defectModel.defectsModelAll.count
            }

            FlowRowItem{
                title: qsTr("当前显示")
                value: root.defectModel.defectsModel.count
            }

            FlowRowItem{
                title: qsTr("卷数")
                value: root.defectModel.currentListModel.count
            }

            FlowRowItem{
                title: qsTr("缺陷类别")
                value: root.defectModel.defectDictModel.count
            }
        }
    }
}
