import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

/**
 * 塔形数据表格显示
 * 显示所有塔形点数据，包括 x, y 坐标和值，保留一位小数
 */
Item {
    id: root
    property var coilModel: null

    // 格式化数值，保留一位小数
    function fmt(val) {
        if (val === undefined || val === null) return "-"
        return Number(val).toFixed(1)
    }

    // 获取指定表面的塔形数据
    function getTaperData(surface) {
        if (!coilModel || !coilModel.coilData) return null
        let data = coilModel.coilData
        // 从 childrenAlarmTaperShape 获取数据（不是 childrenTaperShapePoint）
        if (!data.childrenAlarmTaperShape || data.childrenAlarmTaperShape.length === 0) return null

        for (let i = 0; i < data.childrenAlarmTaperShape.length; i++) {
            let item = data.childrenAlarmTaperShape[i]
            if (item.surface === surface) {
                return item
            }
        }
        return null
    }

    // 获取 S 面数据
    property var taperDataS: getTaperData("S")
    // 获取 L 面数据
    property var taperDataL: getTaperData("L")

    Column {
        anchors.fill: parent
        spacing: 3

        // 标题行
        Row {
            width: parent.width
            height: 22
            spacing: 1

            Repeater {
                model: ["表面", "外塔最高 (x/y/值)", "外塔最低 (x/y/值)", "内塔最高 (x/y/值)", "内塔最低 (x/y/值)", "角度°"]
                Label {
                    width: (parent.width - 5) / 6
                    height: parent.height
                    text: modelData
                    font.bold: true
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    background: Rectangle {
                        color: Material.color(Material.Grey)
                        opacity: 0.3
                    }
                }
            }
        }

        // S 面数据行
        Row {
            width: parent.width
            height: 35
            visible: taperDataS !== null
            spacing: 1

            // 表面
            Label {
                width: (parent.width - 5) / 6
                height: parent.height
                text: "S"
                font.bold: true
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                background: Rectangle { color: Material.color(Material.BlueGrey, Material.Shade50) }
            }

            // 外塔最高
            Column {
                width: (parent.width - 5) / 6
                height: parent.height
                padding: 2
                spacing: 0
                Label {
                    width: parent.width
                    text: taperDataS ? ("x:" + taperDataS.out_taper_max_x) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataS ? ("y:" + taperDataS.out_taper_max_y) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataS ? fmt(taperDataS.out_taper_max_value) : "-"
                    font.pixelSize: 9
                    font.bold: true
                    color: taperDataS && taperDataS.out_taper_max_value > 0 ? Material.color(Material.Red) : Material.color(Material.Green)
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // 外塔最低
            Column {
                width: (parent.width - 5) / 6
                height: parent.height
                padding: 2
                spacing: 0
                Label {
                    width: parent.width
                    text: taperDataS ? ("x:" + taperDataS.out_taper_min_x) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataS ? ("y:" + taperDataS.out_taper_min_y) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataS ? fmt(taperDataS.out_taper_min_value) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // 内塔最高
            Column {
                width: (parent.width - 5) / 6
                height: parent.height
                padding: 2
                spacing: 0
                Label {
                    width: parent.width
                    text: taperDataS ? ("x:" + taperDataS.in_taper_max_x) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataS ? ("y:" + taperDataS.in_taper_max_y) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataS ? fmt(taperDataS.in_taper_max_value) : "-"
                    font.pixelSize: 9
                    font.bold: true
                    color: taperDataS && taperDataS.in_taper_max_value > 0 ? Material.color(Material.Red) : Material.color(Material.Green)
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // 内塔最低
            Column {
                width: (parent.width - 5) / 6
                height: parent.height
                padding: 2
                spacing: 0
                Label {
                    width: parent.width
                    text: taperDataS ? ("x:" + taperDataS.in_taper_min_x) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataS ? ("y:" + taperDataS.in_taper_min_y) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataS ? fmt(taperDataS.in_taper_min_value) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // 角度
            Label {
                width: (parent.width - 5) / 6
                height: parent.height
                text: taperDataS ? (taperDataS.rotation_angle ?? "-") : "-"
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        // L 面数据行
        Row {
            width: parent.width
            height: 35
            visible: taperDataL !== null
            spacing: 1

            // 表面
            Label {
                width: (parent.width - 5) / 6
                height: parent.height
                text: "L"
                font.bold: true
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                background: Rectangle { color: Material.color(Material.BlueGrey, Material.Shade50) }
            }

            // 外塔最高
            Column {
                width: (parent.width - 5) / 6
                height: parent.height
                padding: 2
                spacing: 0
                Label {
                    width: parent.width
                    text: taperDataL ? ("x:" + taperDataL.out_taper_max_x) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataL ? ("y:" + taperDataL.out_taper_max_y) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataL ? fmt(taperDataL.out_taper_max_value) : "-"
                    font.pixelSize: 9
                    font.bold: true
                    color: taperDataL && taperDataL.out_taper_max_value > 0 ? Material.color(Material.Red) : Material.color(Material.Green)
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // 外塔最低
            Column {
                width: (parent.width - 5) / 6
                height: parent.height
                padding: 2
                spacing: 0
                Label {
                    width: parent.width
                    text: taperDataL ? ("x:" + taperDataL.out_taper_min_x) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataL ? ("y:" + taperDataL.out_taper_min_y) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataL ? fmt(taperDataL.out_taper_min_value) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // 内塔最高
            Column {
                width: (parent.width - 5) / 6
                height: parent.height
                padding: 2
                spacing: 0
                Label {
                    width: parent.width
                    text: taperDataL ? ("x:" + taperDataL.in_taper_max_x) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataL ? ("y:" + taperDataL.in_taper_max_y) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataL ? fmt(taperDataL.in_taper_max_value) : "-"
                    font.pixelSize: 9
                    font.bold: true
                    color: taperDataL && taperDataL.in_taper_max_value > 0 ? Material.color(Material.Red) : Material.color(Material.Green)
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // 内塔最低
            Column {
                width: (parent.width - 5) / 6
                height: parent.height
                padding: 2
                spacing: 0
                Label {
                    width: parent.width
                    text: taperDataL ? ("x:" + taperDataL.in_taper_min_x) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataL ? ("y:" + taperDataL.in_taper_min_y) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    width: parent.width
                    text: taperDataL ? fmt(taperDataL.in_taper_min_value) : "-"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            // 角度
            Label {
                width: (parent.width - 5) / 6
                height: parent.height
                text: taperDataL ? (taperDataL.rotation_angle ?? "-") : "-"
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        // 无数据提示
        Label {
            width: parent.width
            height: 30
            text: "暂无塔形数据"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            visible: taperDataS === null && taperDataL === null
            color: Material.color(Material.Grey)
            font.pixelSize: 11
        }
    }
}
