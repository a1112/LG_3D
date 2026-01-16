import QtQuick

Item{
    property int row_:parseInt(index/count_)
    property int col_:parseInt(index%count_)
    x: parseInt(index / count_)*width
    y: parseInt(index%count_)*height
    width: root.width/count_
    height: root.height/count_
    readonly property bool inView: {
        // Simple rectangle overlap check; avoids Qt.rect.intersects availability issues
        const vpX1 = root.viewportX
        const vpY1 = root.viewportY
        const vpX2 = vpX1 + root.viewportW
        const vpY2 = vpY1 + root.viewportH
        const tileX1 = x
        const tileY1 = y
        const tileX2 = tileX1 + width
        const tileY2 = tileY1 + height
        return !(tileX2 <= vpX1 || tileX1 >= vpX2 || tileY2 <= vpY1 || tileY1 >= vpY2)
    }
    // Enable to load immediately; disable to lazy-load by viewport
    readonly property bool shouldLoad: enableParallelLoad ? true : inView
    readonly property var statusNames: ["Null", "Ready", "Loading", "Error"]
    function nowString() {
        const d = new Date()
        return `${d.toLocaleTimeString()}.${("000" + d.getMilliseconds()).slice(-3)}`
    }
    Rectangle{
        anchors.fill: parent
        border.width: 1
        color:"#00000000"
        border.color: "red"
    }
    Image {
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: shouldLoad ? imageUrl+ "?row=" + parseInt(index/count_) + "&col=" + parseInt(index%count_) + "&count=" +count_ : ""
        onStatusChanged: {
            // console.log(`[tile ${index} (${row_},${col_}) ${nowString()}] status=${statusNames[status]}`)
        }
    }

}
