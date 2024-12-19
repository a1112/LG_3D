import QtQuick

Item {
    anchors.fill: parent
    property real centreX:inner_ellipse[0][0]
    property real centreY:inner_ellipse[0][1]
    property real ellipseWidth:Math.min(inner_ellipse[1][0],inner_ellipse[1][1])

    function findPoint(px, py, point_type) {
        // 计算方向向量
        let cx = centreX
        let cy = centreY
        const dx = px - cx
        const dy = py - cy
        var r=ellipseWidth/2-100
        if (point_type === "max_inner"){
             r = ellipseWidth/2-100}
        else if (point_type === "min_inner"){
             r = ellipseWidth/2-200}
        else if (point_type==="max_outer"){
            r = Math.sqrt(dx ** 2 + dy ** 2)-100
        }
        else if (point_type==="min_outer"){
            r = Math.sqrt(dx ** 2 + dy ** 2)-200
        }
        else{
            return Qt.point(px,py);
        }



        // 计算 (cx, cy) 到 (px, py) 的距离
        const d = Math.sqrt(dx ** 2 + dy ** 2)

        // 如果距离为 0，则无法计算方向向量
        if (d === 0) {
            throw new Error("Points cx, cy and px, py cannot be the same.");
        }

        // 归一化方向向量
        const udx = dx / d;
        const udy = dy / d;

        // 计算新点的坐标
        const nx = cx + udx * r;
        const ny = cy + udy * r;

        return Qt.point(nx,ny);
    }
        Repeater{
            model: dataShowCore.pointDbData
            delegate:PointItem{
            }
        }
}
