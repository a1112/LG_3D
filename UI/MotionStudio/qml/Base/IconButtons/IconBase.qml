import QtQuick 2.15
import QtQuick.Controls 2.15
ItemDelegate{
    property alias source: image.source
    Image {
        width: parent.width
        height: parent.height
    id:image
    fillMode: Image.PreserveAspectFit
}
}
