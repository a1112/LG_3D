import QtQuick 2.15
import QtQuick.Controls 2.15
Image {
    fillMode: Image.PreserveAspectFit
    property real currentImageScale: paintedWidth/coreConfig.imageWidth
    id: image
    property ListModel imageObjs
    Item{
        anchors.centerIn: image
        width: image.paintedWidth
        height: image.paintedHeight
        DefectRecView{
        anchors.fill: parent
    }
    }
}
