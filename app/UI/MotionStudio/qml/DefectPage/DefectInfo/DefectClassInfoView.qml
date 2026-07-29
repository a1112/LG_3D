pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
//  类别信息
import "../../Comp/Card"
CardBase {
    clip: true
    id:root
    required property var viewController
    required property var style
    Layout.fillWidth : true
    max_height : 200
    title :  qsTr("缺陷总计")       //"当前卷信息"

    content_body:Item{
        id : col
        width : root.width
        Layout.fillWidth : true
        Layout.fillHeight : true
        visible: root.isShow

        Flow{
            id: flow
            width: parent.width
            Repeater{
                model: root.viewController.defectCoreModel.defectDictModel
                DefectFlowRowItem{
                    style: root.style
                    viewController: root.viewController
                }
            }

            RowLayout{
            width:flow.width
            spacing:5
            CheckDelegate{
                checked: root.viewController.filterCore.fliterShowBgDefect
                onCheckedChanged: {
                root.viewController.filterCore.setFliterShowBgDefect(checked)
                }
                text: qsTr("包括背景")
            }
            Item{
                Layout.fillWidth:true
                height:25
            }

            SelectButtonBase{
                text:qsTr("重置")
                onClicked: {
                    root.viewController.filterCore.reset()
                }
            }
            SelectButtonBase{
                text:qsTr("全选")
                onClicked: {
                    root.viewController.filterCore.showAll(true)
                }
            }
            SelectButtonBase{
                text:qsTr("取消")
                onClicked: {
                    root.viewController.filterCore.showAll(false)
                }
            }
            }
        }

    }
}
