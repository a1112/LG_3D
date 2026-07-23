import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
import SoftList 1.0
Item {
    id:root
    property string softInfoText: ""
    property var softInfo: []
    clip: true
    SoftList{
        id: softList
    }
    ListModel{
        id: model_
    }
    Timer{
        interval: 1000
        running: true
        onTriggered: {
            if (softList.hasNewSoft()){
                flush()
            }
            else{
            restart()
            }
        }
    }
    function flush(){
        model_.clear()
         softInfoText = softList.getSoftList()
        softInfo=JSON.parse(softInfoText)
        for(var i = 0; i < softInfo.length; i++){
            model_.append(softInfo[i])
        }
    }
    ColumnLayout{
        anchors.fill: parent
        ListView{
            spacing: 3
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: model_
            ScrollBar.vertical: ScrollBar{}
            delegate: SoftItem{
                width: root.width
                height: 50
            }
        }
        }
}
