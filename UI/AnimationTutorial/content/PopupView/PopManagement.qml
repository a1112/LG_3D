import QtQuick
import "Export"
import "Connect"
import "DefectClass"
Item {
    anchors.fill: parent

    ConnectDialog{//连接设置
        id:connectDialog
    }
    function popupConnectDialog(){
        connectDialog.open()
    }

    ExportView{
        id:exportView
    }
    function popupExportView(){
        exportView.popup()
    }

        DefectClassPop{
            id:defectClassPop
        }

    function popupDefectClassPop(){
        defectClassPop.popup()
    }
}
