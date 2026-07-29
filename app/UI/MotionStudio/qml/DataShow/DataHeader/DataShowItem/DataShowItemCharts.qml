import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCharts
import "ChartBase"
import "ShowCharts"
import "Base"
DataShowItemBase{
    clip:true
    id:root
    required property var surfaceData
    required property var controller
    required property var style

    visible: root.controller.telescopedJointView
    Layout.fillWidth: true
    property int types:1
    property int drawWidth: width
    property int drawHeight: height-20
    property var lineData: root.surfaceData.lineData || []
    property CoreCharts coreCharts : CoreCharts{
    }
    function findZValue(arr, n) {
        if (arr===undefined) return

      let left = 0;
      let right = arr.length - 2;
      while (left <= right) {
        let mid = Math.floor((left + right) / 2);
        if (arr[mid][0] <= n && (mid + 1 >= arr.length || arr[mid + 1][0] > n)) {
          return arr[mid][2];
        } else if (arr[mid][0] >= n) {
          right = mid - 1;
        } else {
          left = mid + 1;
        }
      }
      return null; // 如果没有找到符合条件的值，返回 null
    }

    function getZValue(z){
        return root.surfaceData.zRawToMm(z)
    }
    function numberOr(value, defaultValue) {
        let numberValue = Number(value)
        return isFinite(numberValue) ? numberValue : defaultValue
    }
    function safeAppend(lineSeri, x, y) {
        let xValue = Number(x)
        let yValue = Number(y)
        if (isFinite(xValue) && isFinite(yValue)) {
            lineSeri.append(xValue, yValue)
        }
    }
    function getXValue(x){
        return ((x - root.surfaceData.inner_circle_centre[0])
                * root.surfaceData.scan3dScaleX).toFixed(0)
    }

    property var line_data: []
    property real chartsHoverdZRawMm: 0
    property int chartsHoverdZRawInt: 0
    property real chartsHoverdZAbsMm: 0
    property real chartsHoverdZRelMm: 0

    function getDistance(x1,y1){
        let i= 1
        if (x1 < root.surfaceData.inner_circle_centre[0])
        {
            i=-1
        }

        return Math.sqrt(
                    Math.pow(x1 - root.surfaceData.inner_circle_centre[0], 2)
                    + Math.pow(
                        y1 - root.surfaceData.inner_circle_centre[1], 2))
                * root.surfaceData.scan3dScaleX * i
    }

    function isFilter(_list,i,n,value){
        for (var j = 1; j < n; j++) {
            if (i-j<0){
                continue
            }
            if (Math.abs(_list[i]-_list[i-j])>value){
                return true
            }
            // if (Math.abs(_list[i]-_list[i-j])<0.2){
            //     return true
            // }
        }
        return false
    }



    function putLineData(lineSeri,x_list,z_list){
        if (!x_list || !z_list || x_list.length === 0 || z_list.length === 0) {
            return
        }

        safeAppend(lineSeri, x_list[0], z_list[0])
        for (var i = 1; i < x_list.length-1; i++) {

            if (isFilter(z_list,i,5,300)){
                continue
                    }
            safeAppend(lineSeri, x_list[i], z_list[i])
        }
        safeAppend(lineSeri, x_list[x_list.length-1], z_list[x_list.length-1])
    }



    function drawMedianLine(){
        medianLine.clear()
        let median = Number(root.surfaceData.medianZ)
        if (!isFinite(median)) {
            drawWr()
            return
        }
        medianLine.append(-20000, median)
        medianLine.append(20000, median)
        drawWr()
    }

    property int wr: root.surfaceData.tower_warning_threshold_up
                     + root.surfaceData.tower_warning_threshold_down
    onWrChanged: {
        drawWr()
    }

    function drawWr(){
    up_wr.clear()
    dowm_wr.clear()
    let median = Number(root.surfaceData.medianZ)
    let up = Number(root.surfaceData.tower_warning_threshold_up)
    let down = Number(root.surfaceData.tower_warning_threshold_down)
    if (!isFinite(median) || !isFinite(up) || !isFinite(down)) {
        return
    }
    up_wr.append(-20000, median + up)
    up_wr.append(20000, median + up)
    dowm_wr.append(-20000, median + down)
    dowm_wr.append(20000, median + down)
    }



    onLineDataChanged: {
        line_data=[]
        l1.clear()
        coreCharts.offsetZ = numberOr(root.surfaceData.medianZ, 0)
        drawMedianLine()
        if (!lineData || lineData.length === 0) {
            return
        }
        let ij=0
        for (var i = 0; i < lineData.length; i++) {
            let item_line_data_x=[]
            let item_line_data_z=[]
            let itemData = lineData[i]
            let points = itemData && itemData.points
            if (!points || points.length === 0) {
                continue
            }
            var j = 0;
            item_line_data_x.push(numberOr(getDistance(points[j][0],points[j][1]), 0)+10)
            item_line_data_z.push(-999)
            for (j; j < points.length; j++) {
                let value = numberOr(getDistance(points[j][0],points[j][1]), 0)
                item_line_data_x.push(value)
                item_line_data_z.push(numberOr(getZValue(points[j][2]), 0))
                ij+=1
            }

            item_line_data_x.push(numberOr(getDistance(points[points.length-1][0],points[points.length-1][1]), 0)-10)
            item_line_data_z.push(-999)
            putLineData(l1,item_line_data_x,item_line_data_z)

        }


    }
    Item{
        id:chartItem
        width:parent.width
        height:parent.height
    ChartViewBase {
        y:-70
        height:parent.height+80
        ValueAxis {
            visible: root.types
            id: valueAxisX
            min: root.numberOr(root.controller.showLeftmm, 0)
            max: Math.max(
                     root.numberOr(root.controller.showRightmm, 1),
                     root.numberOr(root.controller.showLeftmm, 0) + 1)
            tickCount: 11
            titleVisible: false
            gridLineColor: root.style.gridLineColor
            labelsColor: root.style.labelsColor
        }
        ValueAxis {
            visible: root.types
            id: valueAxisY
            min: root.coreCharts.minZ
            max: root.coreCharts.maxZ
            shadesVisible: false
            tickCount: root.coreCharts.tickCountZ + 1
            truncateLabels: false
            gridLineColor: root.style.gridLineColor
            labelsColor: root.style.labelsColor
        }
        id:chartView
        width:parent.width
        animationOptions : ChartView.SeriesAnimations

        antialiasing: true
        LineSeries {
           id:up_wr
           width:1
          style:Qt.DashDotDotLine
          opacity:0.5
            color : "red"
           axisX: valueAxisX
           axisYRight: valueAxisY
        }
        LineSeries {
            id:dowm_wr
            width:1
            opacity:0.5
           style:Qt.DashDotDotLine
             color : "red"
            axisX: valueAxisX
            axisYRight: valueAxisY
         }

        LineSeries {
           id:medianLine
           width:1
          style:Qt.DashDotDotLine
            color : "blue"
           axisX: valueAxisX
           axisYRight: valueAxisY
        }
        LineSeries {
           id:l0
        }
         LineSeries {
             width:1
             color:l0.color
            id:l1
            axisX: valueAxisX
            axisYRight: valueAxisY
         }
         LineSeries {
             width:1
            id:l2
            axisX: valueAxisX
            axisY: valueAxisY
         }
    }
    //拖拽
    Rectangle{
        id:dragLineH
        width:1
        height: root.drawHeight
        visible: isFinite(x)
        x: {
            let left = root.numberOr(root.controller.showLeftmm, 0)
            let right = root.numberOr(root.controller.showRightmm, left + 1)
            let widthValue = Math.max(right - left, 1)
            return 5 + ((root.numberOr(
                             root.controller.hoverdXmm, left) - left)
                        / widthValue) * (chartView.width - 35)
        }
        color: "red"
        opacity:0.8
        onXChanged: {
            if (!root.lineData || root.lineData.length === 0) {
                return
            }
            for (var i = 0; i < root.lineData.length; i++) {
               if (!root.lineData[i] || !root.lineData[i].points) {
                   continue
               }
               let findZ = root.findZValue(
                           root.lineData[i].points, root.controller.hoverdX)
                if(findZ!==null){
                    root.controller.chartsHoverdZmm =
                        root.numberOr(root.getZValue(findZ), 0)
                    root.chartsHoverdZRawInt = parseInt(findZ)
                    root.chartsHoverdZRawMm =
                        findZ * root.surfaceData.scan3dScaleZ
                    root.chartsHoverdZAbsMm =
                        root.surfaceData.zRawToMm(findZ)
                    root.chartsHoverdZRelMm =
                        root.chartsHoverdZAbsMm - root.surfaceData.medianZ
                    break
                }
            }
        }
        Label{
            color: "orange"
            text: root.controller.hoverdXmm.toFixed(1)
            y:dragLineV.y+30
            background: Rectangle{color:"#F12e2e2e"}
        }
    }
    Rectangle{
        id:dragLineV
        width:chartView.width-35
        x:5
        height:1
        visible: isFinite(y)
        y: {
            let range = Math.max(
                        root.numberOr(
                            root.coreCharts.maxZ - root.coreCharts.minZ, 1),
                        1)
            return root.drawHeight
                    - (root.numberOr(
                           root.controller.chartsHoverdZmm,
                           root.coreCharts.minZ) - root.coreCharts.minZ)
                    / range * root.drawHeight
        }
        color: "red"
                  opacity:0.5
        Label{
            color: "green"
            text: "raw " + root.chartsHoverdZRawInt
                  + " | rel " + root.chartsHoverdZRelMm.toFixed(2)
                  + " | abs " + root.chartsHoverdZAbsMm.toFixed(2)
                    background: Rectangle{color:"#F12e2e2e"}
                    x:dragLineH.x+30
                    y:-height
        }
    }

    MouseArea{
        anchors.fill: parent
        onPressed: function(mouse) {
            root.coreCharts.startDrag(mouse.x, mouse.y)
        }
        onPositionChanged: function(mouse) {
           root.coreCharts.dragTo(mouse.x, mouse.y)
        }
        onReleased: function(mouse) {
            root.coreCharts.endDrag(mouse.x, mouse.y)
        }
    }

    WheelHandler {
             onWheel: (event)=>{
                          if (event.angleDelta.y>0){
                            root.coreCharts.tickSizeZ -= 0.5
                          }
                          else {
                            root.coreCharts.tickSizeZ += 0.5
                          }
                      }
         }

    ChartHead{
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
    }
    Item{

        height: parent.height
        x:5
        width: parent.width-35
        HoverHandler{
            onHoveredChanged:
                root.controller.chartHovered = hovered
            onPointChanged: {
                root.controller.hoverPoint = Qt.point(
                            point.position.x / parent.width
                            * root.controller.canvasWidth,
                            root.controller.hoverPoint.y)
            }
        }

    }
}
}
