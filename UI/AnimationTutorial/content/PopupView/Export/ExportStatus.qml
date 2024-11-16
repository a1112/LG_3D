import QtQuick

Item {

        property int downloadNot:0
        property int downloading:1
        property int downloadFinished:2
        property int downloadError:3

        property int currentStatus:downloadNot

        property real progress:0.0


        readonly property bool isNotDownload:currentStatus==downloadNot

        readonly property bool isDownloading:currentStatus==downloading

        readonly property bool isDownloadError:currentStatus==downloadError

        readonly property bool isDownloadFinished:currentStatus==downloadFinished

        property string errorStr:""

        function stratExport(){
            currentStatus=downloading
            progress=0.0
        }

        function setError(errorStr){
            currentStatus=downloadError
            this.errorStr=errorStr
        }

        function setFinished(){
            currentStatus=downloadFinished
        }

        function setNone(){
            currentStatus=downloadNot
        }
}
