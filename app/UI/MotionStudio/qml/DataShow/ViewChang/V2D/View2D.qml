import QtQuick

Item {
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var modelStore
    required property var style

    property var keyList: root.modelStore.allViewKeys  // 2D 视图的切换
    property int netxKetIndex:0
    property string next_key: keyList.length > 0
                              ? keyList[(netxKetIndex + 1) % keyList.length]
                              : ""
    property real zoom: root.dataShowCore.aspectRatio > 0
                        ? width / root.dataShowCore.aspectRatio : 1
    Item{
        width: parent.width
        height: parent.height
        visible: root.dataShowCore.controls.thumbnail_view_2d_enable

    Image{
        id: image
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        sourceSize.width: parent.width
        sourceSize.height: parent.height
        source: root.surfaceData.coilId > 0
                && root.next_key !== ""
                && root.surfaceData.hasViewData(root.next_key)
                ? root.surfaceData.getSouceByKey(root.next_key, true) : ""
        asynchronous:true
    }
    MouseArea{
        anchors.fill:parent
        cursorShape:Qt.PointingHandCursor
        onClicked:{
            root.surfaceData.rootViewto2D()
            root.surfaceData.setViewSource(root.next_key)
            root.netxKetIndex += 1
        }
    }
    }

    ColorValueBar{
        labelColor: root.style.textColor
        height:root.height
    }
}
