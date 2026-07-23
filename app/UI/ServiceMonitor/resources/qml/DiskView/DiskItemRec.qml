import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
Column {
    function getSizeText(size){
        if (size>1000){
            return (size/1000).toFixed(2)+" TB"
        }
        return size.toFixed(2)+" GB"
    }
    RowLayout{
        width: parent.width
        Item{
            height: 1
            width: 5
        }
        Label {
            text: mountpoint
            font.bold: true
            font.pointSize: 10
        }
        Label{
            text: opts
            font.pointSize: 8
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        Label {
            text: fstype
            font.pointSize: 10
        }

        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        // Label {
        //     text: fstype
        //     font.bold: true
        //     font.pointSize: 10
        // }
        Label {
            text: percentage.toFixed(1)+"%"
            font.bold: true
            font.pointSize: 10
        }
    }
    Rectangle{
        width: 190
        height: 14
        color:Qt.rgba(50/255,50/255,50/255,1)

        Rectangle{
            height: parent.height
            width: percentage * parent.width/100
            color:percentage>90?Qt.rgba(218/255,38/255,38/255,1):
                                 Qt.rgba(38/255,160/255,218/255,1)
        }
        Rectangle{
            border.color: "#000000"
            border.width: 2
            anchors.fill: parent
            color: "#00000000"

        }

        Rectangle{
            opacity: 0.89
            anchors.verticalCenter: parent.verticalCenter
            width: 4
            height:parent.height*1.5
            color: Material.color(Material.Orange)
            x:(threshold/100)*parent.width
            onXChanged: {
                threshold = parseInt(x/parent.width*100)
            }

            DragHandler{
                xAxis.minimum: 0
                xAxis.maximum: parent.parent.width
                onActiveChanged: {
                    if(!action){
                    parent.x = Qt.binding(function(){
                        return (threshold/100)*parent.parent.width
                    })

                    }
                }
            }
        }
    }
    Row{
        Label{
            text: "可用: "+getSizeText(free)+", "
        }
        Label{
            text: "共: "+getSizeText(total)
        }
    }
}
