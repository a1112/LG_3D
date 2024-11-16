import QtQuick

Item {


    function fileFolderPath(path) {
        var lastSlashIndex = path.lastIndexOf("/")
        if (lastSlashIndex === -1) {
            lastSlashIndex = path.lastIndexOf("\\")  // Check for Windows-style backslashes
        }
        return lastSlashIndex !== -1 ? path.substring(0, lastSlashIndex) : ""
    }

}
