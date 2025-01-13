import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
// 筛选界面
Item {
    visible:leftCore.fliterEnable
    width: parent.width

    SplitView.preferredHeight:flow.height
    Flow{
        id:flow
        width:parent.width
        Repeater{
            model:global.defectClassProperty.defectDictModel
            DefectClassShowItem{
            }
        }

        RowLayout{
        width:flow.width
        spacing:5
        Item{
            Layout.fillWidth:true
            height:25
        }
        DefectClassShowItem{
            defectClass:global.defectClassProperty.unDefectClassItemModel
            visible:true
        }
        Button{
            implicitHeight:32
            text:"全选"
        }
        Button{
            implicitHeight:32
            text:"取消"
        }
        }



    }
}
