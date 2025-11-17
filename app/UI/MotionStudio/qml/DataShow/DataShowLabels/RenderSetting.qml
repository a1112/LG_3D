import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Pages/Header"
import "Base"
import "../../Comp/Card"
CardBase{
    width:parent.width
max_height: 140
    title: "渲染设置"
content_head_tool:
    CheckDelegate{
        implicitHeight:30
        text: "AOTO"
        scale:0.8
        checked: dataShowCore.autoRender
    }
content_body:
    ColumnLayout {
        width:parent.width
        id:column
        RowSpinBoxItem{
            title : "平面"
            mm_label_visible:false
            from: -9999
            to: 9999
            value:  dataShowCore.medianZ
            onValueChanged: {
                dataShowCore.medianZ = value
            }
        }
        RowSpinBoxItem{
            title : "范围"
            mm_label_visible:false
            from:5
            to:100
            value:  dataShowCore.rangeZ
            onValueChanged: {
                dataShowCore.rangeZ = value
            }
        }
        RowLayout{
            Layout.fillWidth: true
            ComboBox{
                implicitWidth:100
                scale:0.7
                implicitHeight: 30
                model: ["100%","50%","33%"]
                currentIndex: 0
                enabled:!dataShowCore.autoRender
                onCurrentIndexChanged: {
                    dataShowCore.renderScale = 1/(currentIndex+1)
                }
            }
            RowLayout{
                height:30
                width:50
                CheckRec{
                    enabled:!dataShowCore.autoRender
                    height:30
                    scale:0.7
                    text: "渲染"
                    typeIndex:1
                    onClicked: {
                        dataShowCore.renderDrawer()
                        checked=true
                    }
                }
            }
        }
    }
}
