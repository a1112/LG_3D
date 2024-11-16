import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../Header"
import "../../../../types"
BaseSelectPop{
    id:root
    property DateTime dateTime
    width:280
    height:125
    Item{
        anchors.fill:parent
        GridView{
            anchors.fill:parent
            model:dateTime.yearModel
            cellWidth:80
            cellHeight:35
            delegate:CheckRec{
                height:30
                width: 80
                checkColor:dateTime.fullYear==value?Material.color(Material.Orange):"#00000000"
                fillWidth:true
                text:value
                onClicked:{
                    dateTime.fullYear=value
                    root.close()
                }
            }
        }
    }
}

