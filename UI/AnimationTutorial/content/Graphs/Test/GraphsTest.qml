import QtQuick
import QtGraphs


GraphsView {
        id: graphsView
        anchors.fill: parent
        theme: GraphsTheme { theme: GraphsTheme.ThemeLight } // 设置主题

        // 折线图
        LineSeries {
            id: lineSeries
            name: "示例数据"
            axisX: ValueAxis {
                id: axisX
                min: 0
                max: 10
                labelFormat: "%.0f"
                titleText: "X 轴"
            }
            axisY: ValueAxis {
                id: axisY
                min: 0
                max: 20
                labelFormat: "%.0f"
                titleText: "Y 轴"
            }

            // 初始数据点
            XYPoint { x: 0; y: 1 }
            XYPoint { x: 1; y: 3 }
            XYPoint { x: 2; y: 5 }
            XYPoint { x: 3; y: 7 }
            XYPoint { x: 4; y: 9 }
        }
    }
