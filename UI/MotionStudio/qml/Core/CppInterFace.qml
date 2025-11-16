import QtQuick 2.15
import Clipboard 1.0
// import FileDownloader 1.0
Item {
    property Clipboard clipboard:Clipboard{}

   // // property FileDownloader fileDownloader:FileDownloader{}


    // Connections {
    //     target: fileDownloader
    //     onDownloadProgress: console.log("Download progress:", bytesReceived, "/", bytesTotal)
    //     onDownloadFinished: console.log("Download finished")
    //     onDownloadError: console.log("Download error:", errorString)
    // }

}
