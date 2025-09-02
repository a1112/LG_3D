import QtQuick
import QtGraphs

GraphsView {

    anchors.fill: parent
    theme: GraphsTheme {
        colorScheme: GraphsTheme.ColorScheme.Dark
        seriesColors: ["#E0D080", "#B0A060"]
        borderColors: ["#807040", "#706030"]
        grid.mainColor: "#ccccff"
        grid.subColor: "#eeeeff"
        axisY.mainColor: "#ccccff"
        axisY.subColor: "#eeeeff"
    }
    axisX: BarCategoryAxis {
        categories: ["2023", "2024", "2025"]
        lineVisible: false
    }
    axisY: ValueAxis {
        min: 0
        max: 10
        subTickCount: 4
    }
    BarSeries {
        BarSet {
            values: [7, 6, 9]
        }
        BarSet {
            values: [9, 8, 6]
        }
    }
}
