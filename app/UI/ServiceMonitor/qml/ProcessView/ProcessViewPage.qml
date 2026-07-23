import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Controls.Material
import ProcessObj 1.0
Item {
    clip: true
    ProcessObj{
        id:processObj
    }
    Timer{
        interval: 2000
        running: true
        repeat: true
        onTriggered: {
            // let processDatas = processObj.getProcessList()
            // processDatas=JSON.parse(processDatas)
            // proList.clear()
            // for(let i=0;i<processDatas.length;i++){
            //     proList.append(processDatas[i])
            // }
        }
    }
    ListModel{
        id:proList
    }
    ListView{
        anchors.fill: parent
        id:listV
        model: proList
        delegate:ItemDelegate{
            width: window.width
            height: 40
            text: name
        }
    }
}
