import QtQuick
import QtGraphs
import QtQuick.Window
 Window{
    width:300
    height:300
    visible:true
    GraphsView {
        anchors.fill: parent
        axisX: ValueAxis {
            id: xAxis
            max: 8
            tickInterval: 2.0
        }

        axisY: ValueAxis {
            id: yAxis
            max: 4
            tickInterval: 1.0
        }

        AreaSeries {
            upperSeries: LineSeries {
                XYPoint { x: 0; y: 2 }
                XYPoint { x: 1; y: 3.5 }
                XYPoint { x: 2; y: 3.8 }
            }

            lowerSeries: LineSeries {
                XYPoint { x: 0.4; y: 1.5 }
                XYPoint { x: 1; y: 2.5 }
                XYPoint { x: 2.4; y: 3 }
            }
        }
    }
}
