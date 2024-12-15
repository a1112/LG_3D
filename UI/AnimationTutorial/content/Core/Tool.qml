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

}
