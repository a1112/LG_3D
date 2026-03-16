import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtCore
import QtQuick.Dialogs

import "../../Pages/LeftPage/SearchView"
import "../../types"
import "../../Labels"
import "../../Input"
import "../../Pages/Header"
import "../Base"

ApplicationWindow {
    id: root
    width: 650
    height: 500
    visible: false
    title: qsTr("报表导出")
    modality: Qt.ApplicationModal
    flags: Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint

    // 屏幕居中
    x: (Screen.width - width) / 2
    y: (Screen.height - height) / 2

    function openDialog() {
        visible = true
        // 重新计算居中位置
        x = (Screen.width - width) / 2
        y = (Screen.height - height) / 2
        raise()
        requestActivate()
        // 初始化日期时间
        try {
            let mmList = coreModel.getCurrentCoilListModelMinMaxId()
            if (coreModel.currentCoilListModel.count > 0) {
                let frist_item = coreModel.currentCoilListModel.get(0)
                let end_item = coreModel.currentCoilListModel.get(coreModel.currentCoilListModel.count-1)
                // 安全地设置日期时间
                if (end_item && end_item.CreateTime) {
                    let startDate = tool.getDataByJson(end_item.CreateTime)
                    if (startDate && startDate instanceof Date && !isNaN(startDate)) {
                        start_dt.dateTime = startDate
                    }
                }
                if (frist_item && frist_item.CreateTime) {
                    let endDate = tool.getDataByJson(frist_item.CreateTime)
                    if (endDate && endDate instanceof Date && !isNaN(endDate)) {
                        end_dt.dateTime = endDate
                    }
                }
            }
        } catch(e) {
            console.log("Error initializing export dialog dates:", e)
        }
    }

    function closeDialog() {
        visible = false
    }

    property string outputFolder: (""+StandardPaths.writableLocation(StandardPaths.DesktopLocation)).substring(8)
    property string outputName: Qt.formatDateTime(new Date(), "yyyy_MM_dd hh_mm_ss")+".xlsx"
    property string exportUrl: ""
    property string outputBaseUrl: outputFolder+"/"+outputName

    property ExportStatus exportStatus: ExportStatus{}

    background: Rectangle {
        color: Material.backgroundColor
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12

        BaseLabel{
            text:"报表导出"
            color:Material.color(Material.Green)
            font.pointSize: 24
            font.bold:true
            Layout.alignment: Qt.AlignHCenter
        }

        DateTimeSelectItem{
            id:startDate
            title_:"起始导出日期:"
            dateTime_:DateTime{
                id:start_dt
            }
        }

        Rectangle{
            Layout.fillWidth: true
            implicitHeight: 1
            color:Material.color(Material.Blue)
        }

        DateTimeSelectItem{
            id:endDate
            title_:"结束导出日期:"
            dateTime_:DateTime{
                id:end_dt
            }
        }

        SimpleFileInput{
            id:saveFileInput
            text:"导出文件"
            currentFolder:root.outputFolder
            acceptLabel:root.outputName
            placeholderText:"桌面/"+ root.outputName
            nameFilters:[".xlsx"]
            onValueChanged:{
                root.exportStatus.setNone()
            }
        }

        ExportConfigView{
            id:export_data_id
            Layout.fillWidth: true
            implicitHeight:50
        }

        // ========== 快速导出按钮 ==========
        RowLayout{
            Layout.fillWidth: true
            spacing: 10

            BaseLabel{
                text:"快速导出:"
                font.pointSize: 14
            }

            CheckRec{
                text:"今天"
                font.pointSize: 12
                checkColor:Material.color(Material.Green)
                Material.elevation: 6
                Layout.preferredWidth: 100
                enabled:!root.exportStatus.isDownloading
                onClicked:{
                    root.exportStatus.stratExport()
                    let outputUrl = root.outputBaseUrl.replace(".xlsx", "_today.xlsx")
                    root.exportUrl = saveFileInput.value || outputUrl
                    fileDownloader.downloadFile(api.getExportTodayUrl(),root.exportUrl,"")
                }
            }

            CheckRec{
                text:"1小时"
                font.pointSize: 12
                checkColor:Material.color(Material.Cyan)
                Material.elevation: 6
                Layout.preferredWidth: 100
                enabled:!root.exportStatus.isDownloading
                onClicked:{
                    root.exportStatus.stratExport()
                    let outputUrl = root.outputBaseUrl.replace(".xlsx", "_1h.xlsx")
                    root.exportUrl = saveFileInput.value || outputUrl
                    fileDownloader.downloadFile(api.getExport1hUrl(),root.exportUrl,"")
                }
            }

            CheckRec{
                text:"24小时"
                font.pointSize: 12
                checkColor:Material.color(Material.Blue)
                Material.elevation: 6
                Layout.preferredWidth: 100
                enabled:!root.exportStatus.isDownloading
                onClicked:{
                    root.exportStatus.stratExport()
                    let outputUrl = root.outputBaseUrl.replace(".xlsx", "_24h.xlsx")
                    root.exportUrl = saveFileInput.value || outputUrl
                    fileDownloader.downloadFile(api.getExport24hUrl(),root.exportUrl,"")
                }
            }
        }

        Item{
            Layout.fillHeight: true
        }

        RowLayout{
            Layout.fillWidth: true
            spacing: 10

            Item{
                Layout.fillWidth: true
            }

            CheckRec{
                text:root.exportStatus.isDownloading?"导出中...":"导出"
                font.pointSize: 16
                fillWidth: true
                Layout.preferredWidth: 150
                checkColor:Material.color(Material.Orange)
                enabled:!root.exportStatus.isDownloading
                Material.elevation: 12
                onClicked:{
                    root.exportStatus.stratExport()
                    if (!saveFileInput.value){
                        root.exportUrl = root.outputBaseUrl
                    }
                    else{
                        root.exportUrl = saveFileInput.value
                    }
                    let export_data_config=export_data_id.getExportConfig()
                    export_data_config["startDate"] = startDate.dateTime_.dateTimeString
                    export_data_config["endDate"] = endDate.dateTime_.dateTimeString
                    var jsonString = JSON.stringify(export_data_config)

                    fileDownloader.downloadFile(api.getPostExportUrl(),root.exportUrl,jsonString)
                }
            }

            CheckRec{
                text:"关闭"
                font.pointSize: 16
                Layout.preferredWidth: 80
                checkColor:Material.color(Material.Grey)
                Material.elevation: 6
                onClicked:{
                    root.closeDialog()
                }
            }
        }

        // 下载进度行
        RowLayout{
            visible: !root.exportStatus.isNotDownload
            Layout.fillWidth: true

            DownloadingRow{
                finshed:root.exportStatus.isDownloadFinished
                visible: root.exportStatus.isDownloadFinished || root.exportStatus.isDownloading
                progress:root.exportStatus.progress
                exportUrl:root.exportUrl
                Layout.fillWidth: true
            }
            ErrorRow{
                visible: root.exportStatus.isDownloadError
                errorStr:root.exportStatus.errorStr
                Layout.fillWidth: true
            }
        }
    }

    Connections {
        target: fileDownloader
        function onDownloadProgress(bytesReceived,bytesTotal) {
            root.exportStatus.progress = bytesTotal > 0 ? bytesReceived / bytesTotal : 0
        }
        function onDownloadFinished(){
            root.exportStatus.setFinished()
            Qt.openUrlExternally("file:///"+root.exportUrl)
        }
        function onDownloadError(errorString){
            root.exportStatus.setError(errorString)
        }
    }
}
