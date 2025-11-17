import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../Header"
import "../../../../types"
BaseSelectPop{
    id:root

    property DateTime dateTime
    width:150
    height:150
    Item{
        anchors.fill:parent
        GridView{
            anchors.fill:parent
            model:dateTime.monthModel
            cellWidth:40
            cellHeight:30
            delegate:CheckRec{
                height:30
                checkColor:dateTime.month==value?Material.color(Material.Pink):"#00000000"
                fillWidth:true
                width:40
                text:value
                onClicked:{
                    dateTime.month=value
                    root.close()
                }
            }
        }
    }
}

