import QtQuick

Item {
    width: 200
    height:width
    anchors.right:parent.right
    anchors.bottom:parent.bottom
    opacity:0.2

    Image{
    fillMode:Image.PreserveAspectFit
    sourceSize.width:parent.width
    sourceSize.height:parent.height
    source:dataShowCore.changeSource

    }

}
