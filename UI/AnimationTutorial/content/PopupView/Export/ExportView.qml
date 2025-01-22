import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
// import Qt.labs.platform
import QtCore
// import FileDownloader 1.0

import "../../Pages/LeftPage/SearchView"
import "../../types"
import "../../Labels"
import "../../Input"
import "../../Pages/Header"
import "../Base"
PopupBase {
    dim:true
    id:menu
    width: 600
    height:  menu.exportStatus.isNotDownload?360:400
    onOpened:{
        let mmList = coreModel.getCurrentCoilListModelMinMaxId()
        // from_id.value=mmList[0]
        // to_id.value=mmList[1]
        // outputName=Qt.formatDateTime(new Date(), "备份_yyyy_MM_dd hh_mm_ss")
        // ws_id.active=true
    }

    property string outputFolder:(""+StandardPaths.writableLocation(StandardPaths.DesktopLocation)).substring(8)
    property string outputName:Qt.formatDateTime(new Date(), "yyyy_MM_dd hh_mm_ss")+".xlsx"

    property string exportUrl:""
    property string outputBaseUrl:outputFolder+"/"+outputName



    property ExportStatus exportStatus: ExportStatus{}
    ListModel{
        id:coreCoilModel
    }

    ColumnLayout{
        Layout.fillHeight: true
        width:parent.width-20

        BaseLabel{
            text:"报表导出"
            color:Material.color(Material.Green)
            font.pointSize: 30
            font.bold:true
            Layout.alignment: Qt.AlignHCenter
        }

        DateTimeSelectItem{
            id:startDate
            title_:"起始导出日期:"
            dateTime_:DateTime{}
        }
        Rectangle{
            Layout.fillWidth: true
            implicitHeight: 1
            color:Material.color(Material.Blue)
        }
        DateTimeSelectItem{
            id:endDate
            title_:"结束导出日期:"
            dateTime_:DateTime{}
        }
        SimpleFileInput{
            id:saveFileInput
            text:"导出文件"
            currentFolder:menu.outputFolder
            acceptLabel:menu.outputName
            placeholderText:"桌面/"+ menu.outputName
            nameFilters:[".xlsx"]
            onValueChanged:{
                menu.exportStatus.setNone()
            }
        }

        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        ExportConfigView{
            id:export_data_id
         Layout.fillWidth: true
         implicitHeight:50
        }



        RowLayout{
            // DownloadingRow{
            //     finshed:menu.exportStatus.isDownloadFinished
            //     visible: menu.exportStatus.isDownloadFinished || menu.exportStatus.isDownloading
            //     progress:menu.exportStatus.progress
            //     exportUrl:menu.exportUrl
            // }
            // ErrorRow{
            //     visible: menu.exportStatus.isDownloadError
            //     errorStr:menu.exportStatus.errorStr
            // }
            Layout.fillWidth: true
            Item{
                Layout.fillWidth: true
                implicitHeight:1
            }
            // Row{
            //     spacing: 2
            //     Label{
            //         text:"导出类型:"
            //         anchors.verticalCenter: parent.verticalCenter
            //     }
            //     ComboBox{
            //         id:combox_export_type
            //         model: coreModel.exportTypeList
            //         implicitHeight: 30
            //         height: 30
            //     }
            // }
            Item{
                implicitHeight: 5
                implicitWidth: 1
            }

            CheckRec{
                text:menu.exportStatus.isDownloading?"导出中...":"导出"
                font.pointSize: 18
                fillWidth: true
                checkColor:Material.color(Material.Orange)
                enabled:!menu.exportStatus.isDownloading
                Material.elevation: 12
                onClicked:{
                    menu.exportStatus.stratExport()
                    if (!saveFileInput.value){
                        menu.exportUrl = menu.outputBaseUrl
                    }
                    else{
                        menu.exportUrl = saveFileInput.value
                    }
                    let export_data_config=export_data_id.getExportConfig()
                    var jsonString = JSON.stringify(export_data_config)
                                  // 将 JSON 对象转换为字符串
                                  // var jsonString = JSON.stringify(jsonObj);


                    // fileDownloader.downloadFile(api.getPostExportUrl(),menu.exportUrl,jsonString
                    //                             )
                    fileDownloader.downloadFile(api.getExportByDateTimeUrl(startDate.dateTime_.dateTimeString,
                                                                           endDate.dateTime_.dateTimeString
                                                                           ),menu.exportUrl)


                }
            }
        }
        RowLayout{
            visible: !menu.exportStatus.isNotDownload
            Layout.fillWidth: true
            DownloadingRow{
                finshed:menu.exportStatus.isDownloadFinished
                visible: menu.exportStatus.isDownloadFinished || menu.exportStatus.isDownloading
                progress:menu.exportStatus.progress
                exportUrl:menu.exportUrl
            }
            ErrorRow{
                visible: menu.exportStatus.isDownloadError
                errorStr:menu.exportStatus.errorStr
            }
        }

    }
    Connections {
        target: fileDownloader
        function onDownloadProgress(bytesReceived,bytesTotal) {
            console.log("Download progress:", bytesReceived, "/", bytesTotal)
            menu.exportStatus.progress = bytesReceived / bytesTotal

        }
        function onDownloadFinished(){
            console.log("Download finished")
            menu.exportStatus.setFinished()
            Qt.openUrlExternally("file:///"+menu.exportUrl)

        }
        function onDownloadError(errorString){
            console.log("Download error:", errorString)
            menu.exportStatus.setError(errorString)
        }
    }
}
