import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Labels"
import "../../Pages/Header"
RowLayout{
    id:root
    Layout.fillWidth: true
    property real progress:0.0
    property bool finshed:false
    property string exportUrl:""


    BaseLabel{
        text:"导出进度："
    }

    ProgressBar{
        Layout.fillWidth: true
        from :0.0
        to:1.0
        value:root.progress
            indeterminate: root.progress<0.001
    }
    BaseLabel{
        text:""+(parseInt(root.progress*100)) +"%"
    }
    CheckRecButton{
        visible:root.finshed
        text:"打开"
        onClicked:{
            Qt.openUrlExternally("file:///"+root.exportUrl)
        }
    }
    CheckRecButton{
        visible:root.finshed
        text:"打开位置..."
        onClicked:{
            Qt.openUrlExternally("file:///"+tool.fileFolderPath(root.exportUrl))
        }
    }
}
