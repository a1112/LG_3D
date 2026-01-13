import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCharts
import "../../Labels"
import "../../Input"

ApplicationWindow {
    id: root
    visible: false
    width: 1300
    height: 720
    title: qsTr("设备曲线")

    property int defaultLimit: 200
    property int selectedIndex: -1
    property bool drawS: true
    property bool drawL: true
    property bool drawLaser: true
    property bool drawWidth: true
    property ListModel curveModel: ListModel {}
    property real totalLengthAvg: 0
    property real distanceSAvg: 0
    property real distanceLAvg: 0

    function openCurve(){
        visible = true
        initRange()
        loadCurve()
    }

    function initRange(){
        if (coreModel && coreModel.realCoilListModel && coreModel.realCoilListModel.count > 0){
            startInput.text = coreModel.getMinCoilId()
            endInput.text = coreModel.getMaxCoilId()
        }
        limitInput.text = defaultLimit
    }

    function loadCurve(){
        let startId = parseInt(startInput.text)
        let endId = parseInt(endInput.text)
        let limit = parseInt(limitInput.text)
        api.getPlcCurveAllData(startId, endId, limit,
            function(result){
                let payload = {}
                try { payload = JSON.parse(result) } catch (e) { payload = {} }
                curveModel.clear()
                totalLengthAvg = 0
                distanceSAvg = 0
                distanceLAvg = 0
                if (!payload.items){
                    updateChart()
                    return
                }
                let totalSum = 0
                let totalCount = 0
                let distSSum = 0
                let distSCount = 0
                let distLSum = 0
                let distLCount = 0
                for (let i = 0; i < payload.items.length; i++) {
                    let item = payload.items[i]
                    let widthVal = Number(item.width_)
                    let distS = Number(item.median_3d_mm_S)
                    let distL = Number(item.median_3d_mm_L)
                    let totalLen = NaN
                    if (isFinite(widthVal) && isFinite(distS) && isFinite(distL)) {
                        totalLen = widthVal + distS + distL
                        totalSum += totalLen
                        totalCount += 1
                    }
                    if (isFinite(distS)) {
                        distSSum += distS
                        distSCount += 1
                    }
                    if (isFinite(distL)) {
                        distLSum += distL
                        distLCount += 1
                    }
                    curveModel.append({
                        coil_id: item.coil_id,
                        time: item.time ? item.time : "",
                        location_S: item.location_S,
                        location_L: item.location_L,
                        location_laser: item.location_laser,
                        median_3d_mm_S: item.median_3d_mm_S,
                        median_3d_mm_L: item.median_3d_mm_L,
                        median_3d_mm_avg: item.median_3d_mm_avg,
                        width_: item.width_,
                        total_length: totalLen,
                        total_error: 0,
                        distance_s_error: 0,
                        distance_l_error: 0
                    })
                }
                totalLengthAvg = totalCount > 0 ? totalSum / totalCount : 0
                distanceSAvg = distSCount > 0 ? distSSum / distSCount : 0
                distanceLAvg = distLCount > 0 ? distLSum / distLCount : 0
                for (let j = 0; j < curveModel.count; j++) {
                    let row = curveModel.get(j)
                    let lenVal = Number(row.total_length)
                    curveModel.setProperty(j, "total_error", isFinite(lenVal) ? (lenVal - totalLengthAvg) : NaN)
                    let sVal = Number(row.median_3d_mm_S)
                    curveModel.setProperty(j, "distance_s_error", isFinite(sVal) ? (sVal - distanceSAvg) : NaN)
                    let lVal = Number(row.median_3d_mm_L)
                    curveModel.setProperty(j, "distance_l_error", isFinite(lVal) ? (lVal - distanceLAvg) : NaN)
                }
                updateChart()
            },
            function(err){
                console.log("getPlcCurveAllData error", err)
                curveModel.clear()
                totalLengthAvg = 0
                distanceSAvg = 0
                distanceLAvg = 0
                updateChart()
            }
        )
    }

    function loadAround(coilId){
        if (!isFinite(coilId)){
            return
        }
        let startId = Math.max(1, coilId - 5)
        let endId = coilId + 4
        startInput.text = startId
        endInput.text = endId
        limitInput.text = 10
        loadCurve()
    }

    function updateChart(){
        seriesS.clear()
        seriesL.clear()
        seriesLaser.clear()
        seriesDistanceS.clear()
        seriesDistanceL.clear()
        seriesWidth.clear()

        let minX = Number.POSITIVE_INFINITY
        let maxX = Number.NEGATIVE_INFINITY
        let minY = Number.POSITIVE_INFINITY
        let maxY = Number.NEGATIVE_INFINITY

        for (let i = 0; i < curveModel.count; i++) {
            let row = curveModel.get(i)
            let x = Number(row.coil_id)
            if (!isFinite(x)) {
                continue
            }
            if (drawS) {
                let yS = Number(row.location_S)
                if (isFinite(yS)) {
                    seriesS.append(x, yS)
                    if (yS < minY) minY = yS
                    if (yS > maxY) maxY = yS
                }
            }
            if (drawL) {
                let yL = Number(row.location_L)
                if (isFinite(yL)) {
                    seriesL.append(x, yL)
                    if (yL < minY) minY = yL
                    if (yL > maxY) maxY = yL
                }
            }
            if (drawLaser) {
                let yLa = Number(row.location_laser)
                if (isFinite(yLa)) {
                    seriesLaser.append(x, yLa)
                    if (yLa < minY) minY = yLa
                    if (yLa > maxY) maxY = yLa
                }
            }
            let yDs = Number(row.median_3d_mm_S)
            if (isFinite(yDs)) {
                seriesDistanceS.append(x, yDs)
                if (yDs < minY) minY = yDs
                if (yDs > maxY) maxY = yDs
            }
            let yDl = Number(row.median_3d_mm_L)
            if (isFinite(yDl)) {
                seriesDistanceL.append(x, yDl)
                if (yDl < minY) minY = yDl
                if (yDl > maxY) maxY = yDl
            }
            if (drawWidth) {
                let yW = Number(row.width_)
                if (isFinite(yW)) {
                    seriesWidth.append(x, yW)
                    if (yW < minY) minY = yW
                    if (yW > maxY) maxY = yW
                }
            }
            if (x < minX) minX = x
            if (x > maxX) maxX = x
        }

        if (!isFinite(minX) || !isFinite(minY)) {
            axisX.min = 0
            axisX.max = 1
            axisY.min = 0
            axisY.max = 1
            return
        }

        axisX.min = minX
        axisX.max = maxX
        if (minY === maxY) {
            axisY.min = minY - 1
            axisY.max = maxY + 1
        } else {
            axisY.min = minY
            axisY.max = maxY
        }
    }

    ColumnLayout{
        anchors.fill: parent
        spacing: 8

        RowLayout{
            Layout.fillWidth: true
            Layout.margins: 10

            Label{
                text: qsTr("设备曲线")
                font.bold: true
                font.pointSize: 14
            }

            Item{ Layout.fillWidth: true }

            CheckBox{
                text: qsTr("S端位置")
                checked: drawS
                onCheckedChanged: {
                    drawS = checked
                    updateChart()
                }
            }
            CheckBox{
                text: qsTr("L端位置")
                checked: drawL
                onCheckedChanged: {
                    drawL = checked
                    updateChart()
                }
            }
            CheckBox{
                text: qsTr("激光距离")
                checked: drawLaser
                onCheckedChanged: {
                    drawLaser = checked
                    updateChart()
                }
            }
            CheckBox{
                text: qsTr("\u5bbd\u5ea6")
                checked: drawWidth
                onCheckedChanged: {
                    drawWidth = checked
                    updateChart()
                }
            }
        }

        RowLayout{
            Layout.fillWidth: true
            Layout.margins: 10

            Label{ text: qsTr("起始ID") }
            TextFieldBase{ id: startInput; implicitWidth: 110 }
            Label{ text: qsTr("结束ID") }
            TextFieldBase{ id: endInput; implicitWidth: 110 }
            Label{ text: qsTr("数量") }
            TextFieldBase{ id: limitInput; implicitWidth: 80 }
            Button{
                text: qsTr("刷新")
                onClicked: loadCurve()
            }
            Button{
                text: qsTr("关闭")
                onClicked: root.visible = false
            }
        }

        ChartView{
            id: chart
            Layout.fillWidth: true
            Layout.preferredHeight: 320
            antialiasing: true
            legend.visible: true

            ValueAxis{ id: axisX; titleText: qsTr("Coil ID") }
            ValueAxis{ id: axisY; titleText: qsTr("值") }

            LineSeries{
                id: seriesS
                axisX: axisX
                axisY: axisY
                name: qsTr("S端位置")
                color: "#3ba4ff"
                visible: drawS
            }
            LineSeries{
                id: seriesL
                axisX: axisX
                axisY: axisY
                name: qsTr("L端位置")
                color: "#5ad16b"
                visible: drawL
            }
            LineSeries{
                id: seriesLaser
                axisX: axisX
                axisY: axisY
                name: qsTr("激光距离")
                color: "#ff9b3b"
                visible: drawLaser
            }
            LineSeries{
                id: seriesDistanceS
                axisX: axisX
                axisY: axisY
                name: qsTr("\u0053\u7aef\u8ddd\u79bb")
                color: "#ff5a5a"
            }
            LineSeries{
                id: seriesDistanceL
                axisX: axisX
                axisY: axisY
                name: qsTr("\u004c\u7aef\u8ddd\u79bb")
                color: "#ff6fc1"
            }
            LineSeries{
                id: seriesWidth
                axisX: axisX
                axisY: axisY
                name: qsTr("\u5bbd\u5ea6")
                color: "#8bd450"
                visible: drawWidth
            }
        }

        Rectangle{
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            border.width: 1
            border.color: "#334455"

            ColumnLayout{
                anchors.fill: parent
                spacing: 0

                Rectangle{
                    Layout.fillWidth: true
                    height: 30
                    color: "#1b2a3a"

                    RowLayout{
                        anchors.fill: parent
                        spacing: 8
                        Label{ Layout.preferredWidth: 90; text: qsTr("Coil ID"); color: "white" }
                        Label{ Layout.preferredWidth: 160; text: qsTr("时间"); color: "white" }
                        Label{ Layout.preferredWidth: 90; text: qsTr("宽度"); color: "white" }
                        Label{ Layout.preferredWidth: 110; text: qsTr("S端位置"); color: "white" }
                        Label{ Layout.preferredWidth: 110; text: qsTr("L端位置"); color: "white" }
                        Label{ Layout.preferredWidth: 110; text: qsTr("激光距离"); color: "white" }
                        Label{ Layout.preferredWidth: 120; text: qsTr("S端距离(mm)"); color: "white" }
                        Label{ Layout.preferredWidth: 120; text: qsTr("L端距离(mm)"); color: "white" }
                        Label{ Layout.preferredWidth: 140; text: qsTr("总长"); color: "white" }
                        Label{ Layout.preferredWidth: 150; text: qsTr("平均误差"); color: "white" }
                        Label{ Layout.preferredWidth: 150; text: qsTr("S端距离平均误差"); color: "white" }
                        Label{ Layout.preferredWidth: 150; text: qsTr("L端距离平均误差"); color: "white" }
                    }
                }

                ListView{
                    id: tableView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: curveModel
                    currentIndex: selectedIndex
                    delegate: Rectangle{
                        width: tableView.width
                        height: 28
                        color: index === selectedIndex ? "#1f3b52" : (index % 2 === 0 ? "#0f1a24" : "#13212f")

                        RowLayout{
                            anchors.fill: parent
                            spacing: 8
                            Label{ Layout.preferredWidth: 90; text: coil_id; color: "white" }
                            Label{ Layout.preferredWidth: 160; text: time; color: "white" }
                            Label{ Layout.preferredWidth: 90; text: formatValue(width_); color: "white" }
                            Label{ Layout.preferredWidth: 110; text: formatValue(location_S); color: "white" }
                            Label{ Layout.preferredWidth: 110; text: formatValue(location_L); color: "white" }
                            Label{ Layout.preferredWidth: 110; text: formatValue(location_laser); color: "white" }
                            Label{ Layout.preferredWidth: 120; text: formatValue(median_3d_mm_S); color: "white" }
                            Label{ Layout.preferredWidth: 120; text: formatValue(median_3d_mm_L); color: "white" }
                            Label{ Layout.preferredWidth: 140; text: formatValue(total_length); color: "white" }
                            Label{ Layout.preferredWidth: 150; text: formatValue(total_error); color: "white" }
                            Label{ Layout.preferredWidth: 150; text: formatValue(distance_s_error); color: "white" }
                            Label{ Layout.preferredWidth: 150; text: formatValue(distance_l_error); color: "white" }
                        }

                        MouseArea{
                            anchors.fill: parent
                            onClicked:{
                                selectedIndex = index
                                loadAround(Number(coil_id))
                            }
                        }
                    }
                }
            }
        }
    }

    function formatValue(val){
        let num = Number(val)
        if (!isFinite(num)) return ""
        return num.toFixed(3)
    }

 
}
