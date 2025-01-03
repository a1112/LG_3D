import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
ItemDelegate {
    id:root
    property string title: "数据"
    property string valueText: ""
    property string valueColor: Material.color(Material.Green)
    Frame{
        anchors.fill: parent
    }
    function success_function(delay_) {
        // 连接成功
        valueText=delay_+"  ms"
        valueColor=Material.color(Material.Green)
                coreModel.coreGlobalError.errorState["网络"][index] = 0

    }

    function fail_function(delay_) {
        valueText= "连接错误"
        coreModel.coreGlobalError.errorState["网络"][index] = 3
        valueColor=Material.color(Material.Red)
    }
    Timer{
        repeat:true
        running:true
        interval:5000
        triggeredOnStart:true
        onTriggered:{
            api.__getDelay__(port,success_function,fail_function)
        }
    }

    // Frame{
    //     anchors.fill: parent
    // }
    RowLayout{
        anchors.fill: parent
        Label{
            text:root.title
        }
        Label{
            text: ":"
        }
        Label{
            color: root.valueColor
            font.bold:true
            font.pixelSize: 20
            text: root.valueText
        }
    }

}
