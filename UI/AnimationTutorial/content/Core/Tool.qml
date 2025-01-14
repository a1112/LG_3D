import QtQuick

Item {

    function url_to_str(url){
        return url.toString().substring(8)
    }

    function fileFolderPath(path) {
        var lastSlashIndex = path.lastIndexOf("/")
        if (lastSlashIndex === -1) {
            lastSlashIndex = path.lastIndexOf("\\")  // Check for Windows-style backslashes
        }
        return lastSlashIndex !== -1 ? path.substring(0, lastSlashIndex) : ""
    }

    function for_list_model(list_model,func){
        for (let i=0;i<list_model.count;i++){
            if (func(list_model.get(i)) === true)return
        }
    }
}
