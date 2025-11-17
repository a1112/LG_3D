import QtQuick

Item{
    property int row_:parseInt(index/count_)
    property int col_:parseInt(index%count_)
    x: parseInt(index / count_)*width
    y: parseInt(index%count_)*height
    width: root.width/count_
    height: root.height/count_
    Rectangle{
        anchors.fill: parent
        border.width: 1
        color:"#00000000"
        border.color: "red"
    }
Image {
    width: parent.width
    height: parent.height
    source: imageUrl+ "?row=" + parseInt(index/count_) + "&col=" + parseInt(index%count_) + "&count=" +count_
    // sourceClipRect:Qt.rect(
    //                     row_*source_item_width,
    //                    col_*source_item_height,
    //                    source_item_width,
    //                    source_item_height)
    asynchronous: true
    fillMode: Image.PreserveAspectFit
    // sourceSize.width:parent.width
    // sourceSize.height:parent.width
}
}
