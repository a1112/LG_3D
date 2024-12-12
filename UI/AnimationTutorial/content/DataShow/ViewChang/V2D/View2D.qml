import QtQuick

Item {
    id:root
    property var keyList:coreModel.allViewKeys  // 2D 视图的切换
    property int netxKetIndex:0
    property string next_key: keyList[(netxKetIndex+1)%keyList.length]
    property real zoom: width/dataShowCore.aspectRatio
    Image{
        id: image
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        sourceSize.width: parent.width
        sourceSize.height: parent.height
        source:surfaceData.getSouceByKey(next_key)
    }
    MouseArea{
        anchors.fill:parent

        cursorShape:Qt.PointingHandCursor
        onClicked:{
            surfaceData.rootViewto2D()
            surfaceData.setViewSource(next_key)
            netxKetIndex+=1
        }
    }
    ColorValueBar{
        height:root.height
    }
}
