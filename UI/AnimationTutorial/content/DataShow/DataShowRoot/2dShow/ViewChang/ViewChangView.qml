import QtQuick
/*
    2D功能切换
*/
import QtQuick
import QtQuick.Controls
Item {
    property var keyList:coreModel.allViewKeys
    property int netxKetIndex:0
    property string next_key: keyList[(netxKetIndex+1)%keyList.length]
    id:root
    width: 400
    height: width/dataShowCore.aspectRatio

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

            surfaceData.setViewSource(next_key)
            netxKetIndex+=1

        }
    }

    ColorValueBar{
        height:root.height
    }
}
