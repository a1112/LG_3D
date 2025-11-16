import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
//  类别信息
import "../../Base"
import "../../Comp/Card"
CardBase {
    clip: true
    id:root
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
                model:defectViewCore.defectCoreModel.defectDictModel   // global.defectClassProperty.defectDictModel
                DefectFlowRowItem{
                }
            }

            RowLayout{
            width:flow.width
            spacing:5
            CheckDelegate{
                checked: defectViewCore.filterCore.fliterShowBgDefect
                onCheckedChanged: {
                defectViewCore.filterCore.setFliterShowBgDefect(checked)
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
                    defectViewCore.filterCore.reset()
                }
            }
            SelectButtonBase{
                text:qsTr("全选")
                onClicked: {
                    defectViewCore.filterCore.showAll(true)
                }
            }
            SelectButtonBase{
                text:qsTr("取消")
                onClicked: {
                    defectViewCore.filterCore.showAll(false)
                }
            }
            }
        }

    }
}
