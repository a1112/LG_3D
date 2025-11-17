import QtQuick 2.15
import QtCharts
ChartView {
    id:chart
    backgroundColor: "#00000000"
    margins.bottom : 0
        margins.left : 0
        margins.right : 0
        margins.top : 0
    antialiasing: true
    dropShadowEnabled:true
    plotArea:Qt.rect(5, 70, chart.width-35, drawHeight)
}
