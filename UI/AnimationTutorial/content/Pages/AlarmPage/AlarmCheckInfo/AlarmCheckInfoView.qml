import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Comp/Card"
import "../../../Pages/Header"
CardBase {
    id: root
    height: 35
    title: "判级"
    property int currentPortInt: 0

    function setCurrentPortInt(currentPortInt){
        currentPortInt = currentPortInt
    }

    // title_vis:false
    content_body: Item{
        RowLayout{
            width :root.width
            height:30
            anchors.fill: parent
                Item{
                    width:20
                    height:5
                }
                CheckRec{
                    fillWidth: true
                    text : "返修"
                    color: currentPortInt == -1? "red": coreStyle.textColor
                    checkColor: currentPortInt == -1?color:"#00000000"
                    onClicked:{
                        currentPortInt=-1
                    }
                }
                CheckRec{
                    fillWidth: true
                    text : "未确认"
                    color: currentPortInt == 0? "yellow": coreStyle.textColor
                    checkColor: currentPortInt == 0?color:"#00000000"
                    onClicked:{
                        currentPortInt=0
                    }
                }
                CheckRec{
                    fillWidth: true
                    text : "通过"
                    color: currentPortInt == 1? "green": coreStyle.textColor
                    checkColor: currentPortInt == 1?color:"#00000000"
                    onClicked:{
                        currentPortInt=1
                    }
                }
            }


    }
}
