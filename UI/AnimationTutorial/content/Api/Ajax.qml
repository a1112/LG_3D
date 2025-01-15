import QtQuick 2.15

Item {

    function get(url, success, failure)
    {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", url);
        xhr.onreadystatechange = function() {
            handleResponse(xhr, success, failure);
        }
        xhr.send();
    }

    // POST
    function post(url, arg, success, failure)
    {

        // WARNING: For POST requests, body is set to null by browsers.
        var data = JSON.stringify(arg)

        var xhr = new XMLHttpRequest()
        xhr.withCredentials = true
        xhr.onreadystatechange = function() {
            handleResponse(xhr, success, failure);
        }
        xhr.open("POST", url);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.send(data);
//        // WARNING: For POST requests, body is set to null by browsers.
//        data = JSON.stringify(data)

//        var xhr = new XMLHttpRequest()
//        xhr.withCredentials = true

//        xhr.addEventListener("readystatechange", function() {
//          if(this.readyState === 4) {
//            console.log(this.responseText)
//          }
//        })

//        xhr.open("POST", url,true)
//        xhr.setRequestHeader("Content-Type", "application/json")

//        xhr.send(data)
//        xhr.open("POST", url)
////        xhr.setRequestHeader("Content-Length", arg.length)
////        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded;")  //用POST的时候一定要有这句
//        xhr.onreadystatechange = function() {
//            handleResponse(xhr, success, failure)
//        }
//        xhr.send(data)
    }


    // 处理返回值
    function handleResponse(xhr, success, failure){
        if (xhr.readyState === XMLHttpRequest.DONE) {
            if (xhr.status ===  200){
                if (success !== null && success !== undefined)
                {
                    var result = xhr.responseText
                                   success(result)
                }
            }
            else{
                if (failure !== null && failure !== undefined)
                    failure(xhr.responseText, xhr.status)
            }
        }
    }
    // function downloadFile(url, fileName) {
    //     var xhr = new XMLHttpRequest();
    //     xhr.open("GET", url, true);
    //     xhr.responseType = "blob"; // 确保以二进制数据格式接收
    //     xhr.onreadystatechange = function() {
    //         console.log("Download status: " + xhr.status);
    //         if (xhr.status === 200) {
    //             saveFile(xhr.response, fileName);
    //         } else {
    //             console.log("Download failed: " + xhr.status);
    //         }
    //     };
    //     xhr.send();
    // }

    // function saveFile(data, fileName) {
    //     console.log(data)
    //     var fileUrl = URL.createObjectURL(data);
    //     var a = document.createElement("a");
    //     a.href = fileUrl;
    //     a.download = fileName;
    //     document.body.appendChild(a);
    //     a.click();
    //     setTimeout(function() {
    //         document.body.removeChild(a);
    //         URL.revokeObjectURL(fileUrl);
    //     }, 0);
    // }

    // Connections {
    //     target: fileDownloader
    //     onDownloadProgress: console.log("Download progress:", bytesReceived, "/", bytesTotal)
    //     onDownloadFinished: console.log("Download finished")
    //     onDownloadError: console.log("Download error:", errorString)
    // }

    Component.onCompleted: {
        // console.log("download test")
        // fileDownloader.downloadFile("http://127.0.0.1:6011/download_test", "file.zip")

    }

}
