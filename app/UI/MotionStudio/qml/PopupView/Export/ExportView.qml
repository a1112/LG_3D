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

    required property var adaptiveMetrics
    required property var style
    required property var modelStore
    required property var toolService
    required property var apiClient
    required property var downloadClient

    width: root.adaptiveMetrics.boundedWidth(650, 520, 820)
    height: root.adaptiveMetrics.boundedHeight(500, 380, 680)
    visible: false
    title: qsTr("报表导出")
    modality: Qt.ApplicationModal
    flags: Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint

    // 屏幕居中
    x: Math.max(0, (Screen.width - width) / 2)
    y: Math.max(0, (Screen.height - height) / 2)

    function openDialog() {
        visible = true
        // 重新计算居中位置
        x = Math.max(0, (Screen.width - width) / 2)
        y = Math.max(0, (Screen.height - height) / 2)
        raise()
        requestActivate()
        // 初始化日期时间
        try {
            if (root.modelStore.currentCoilListModel.count > 0) {
                let firstItem = root.modelStore.currentCoilListModel.get(0)
                let endItem = root.modelStore.currentCoilListModel.get(
                            root.modelStore.currentCoilListModel.count - 1)
                // 安全地设置日期时间
                if (endItem && endItem.CreateTime) {
                    let startDate = root.toolService.getDataByJson(endItem.CreateTime)
                    if (startDate && startDate instanceof Date && !isNaN(startDate)) {
                        start_dt.setDate(startDate)
                    }
                }
                if (firstItem && firstItem.CreateTime) {
                    let endDate = root.toolService.getDataByJson(firstItem.CreateTime)
                    if (endDate && endDate instanceof Date && !isNaN(endDate)) {
                        end_dt.setDate(endDate)
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

    function refreshOutputName() {
        outputName = Qt.formatDateTime(new Date(), "yyyy_MM_dd hh_mm_ss") + ".xlsx"
    }

    function quickOutputUrl(suffix) {
        refreshOutputName()
        return outputBaseUrl.replace(".xlsx", suffix + ".xlsx")
    }

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
            style: root.style
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
            style: root.style
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
            style: root.style
            toolService: root.toolService
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
                style: root.style
                text:"今天"
                font.pointSize: 12
                checkColor:Material.color(Material.Green)
                Material.elevation: 6
                Layout.preferredWidth: 100
                enabled:!root.exportStatus.isDownloading
                onClicked:{
                    root.exportStatus.startExport()
                    let outputUrl = root.quickOutputUrl("_today")
                    root.exportUrl = saveFileInput.value || outputUrl
                    root.downloadClient.downloadFile(
                                root.apiClient.getExportTodayUrl(), root.exportUrl)
                }
            }

            CheckRec{
                style: root.style
                text:"1小时"
                font.pointSize: 12
                checkColor:Material.color(Material.Cyan)
                Material.elevation: 6
                Layout.preferredWidth: 100
                enabled:!root.exportStatus.isDownloading
                onClicked:{
                    root.exportStatus.startExport()
                    let outputUrl = root.quickOutputUrl("_1h")
                    root.exportUrl = saveFileInput.value || outputUrl
                    root.downloadClient.downloadFile(
                                root.apiClient.getExport1hUrl(), root.exportUrl)
                }
            }

            CheckRec{
                style: root.style
                text:"24小时"
                font.pointSize: 12
                checkColor:Material.color(Material.Blue)
                Material.elevation: 6
                Layout.preferredWidth: 100
                enabled:!root.exportStatus.isDownloading
                onClicked:{
                    root.exportStatus.startExport()
                    let outputUrl = root.quickOutputUrl("_24h")
                    root.exportUrl = saveFileInput.value || outputUrl
                    root.downloadClient.downloadFile(
                                root.apiClient.getExport24hUrl(), root.exportUrl)
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
                style: root.style
                text:root.exportStatus.isDownloading?"导出中...":"导出"
                font.pointSize: 16
                fillWidth: true
                Layout.preferredWidth: 150
                checkColor:Material.color(Material.Orange)
                enabled:!root.exportStatus.isDownloading
                Material.elevation: 12
                onClicked:{
                    const startValue = startDate.dateTime_.getCurrentDate()
                    const endValue = endDate.dateTime_.getCurrentDate()
                    if (startValue > endValue) {
                        root.exportStatus.setError("起始时间不能晚于结束时间")
                        return
                    }

                    root.exportStatus.startExport()
                    if (!saveFileInput.value){
                        root.refreshOutputName()
                        root.exportUrl = root.outputBaseUrl
                    }
                    else{
                        root.exportUrl = saveFileInput.value
                    }
                    let export_data_config=export_data_id.getExportConfig()
                    export_data_config["startDate"] = startDate.dateTime_.dateTimeString
                    export_data_config["endDate"] = endDate.dateTime_.dateTimeString
                    var jsonString = JSON.stringify(export_data_config)

                    root.downloadClient.downloadFile(
                                root.apiClient.getPostExportUrl(),
                                root.exportUrl,
                                jsonString)
                }
            }

            CheckRec{
                style: root.style
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
                style: root.style
                toolService: root.toolService
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
        target: root.downloadClient
        function onDownloadProgress(bytesReceived,bytesTotal) {
            root.exportStatus.progress = bytesTotal > 0 ? bytesReceived / bytesTotal : 0
        }
        function onDownloadFinished(){
            root.exportStatus.setFinished()
            if (root.exportUrl) {
                Qt.openUrlExternally("file:///" + root.exportUrl)
            }
        }
        function onDownloadError(errorString){
            root.exportStatus.setError(errorString)
        }
    }
}
