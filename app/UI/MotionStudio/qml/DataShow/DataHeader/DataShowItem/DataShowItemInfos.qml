import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Base"
import "../../DataShowLabels/Base"

DataShowItemBase {
    id: root

    required property var alarmInfo

    function levelColor(level) {
        if (level >= 3) {
            return Material.color(Material.Red)
        }
        if (level === 2) {
            return Material.color(Material.Yellow)
        }
        if (level === 1) {
            return Material.color(Material.Green)
        }
        return Material.color(Material.Grey)
    }

    function fmt(value, digits) {
        if (value === undefined || value === null) {
            return "--"
        }
        if (!isFinite(value)) {
            return "--"
        }
        return Number(value).toFixed(digits === undefined ? 1 : digits)
    }

    readonly property real taperOut: root.alarmInfo.coreTaperShape.outTaper
    readonly property real taperIn: root.alarmInfo.coreTaperShape.innerTaper
    readonly property int taperLevel: Math.max(root.taperOut > 75 ? 3 : 1,
                                               root.taperIn > 10 ? 3 : 1)

    readonly property real flatDiameterMm: root.alarmInfo.coreFlatRoll.innerDiameterMm
    readonly property int flatLevel: root.flatDiameterMm > 0 && root.flatDiameterMm < 680
                                     ? 2 : root.flatDiameterMm > 0 ? 1 : 0

    RowLayout {
        anchors.fill: parent
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 6

            RowLayout {
                spacing: 8
                Rectangle {
                    width: 10
                    height: 10
                    radius: 5
                    color: root.levelColor(root.taperLevel)
                }
                TitleLabel {
                    text: "塔形报警"
                }
            }

            RowLayout {
                KeyLabel { text: "外塔(mm)" }
                ValueLabel { text: root.fmt(root.taperOut, 1) }
                KeyLabel { text: "内塔(mm)" }
                ValueLabel { text: root.fmt(root.taperIn, 1) }
            }

            RowLayout {
                KeyLabel { text: "S端外塔" }
                ValueLabel {
                    text: root.alarmInfo.coreTaperShape.s.hasData
                          ? root.fmt(root.alarmInfo.coreTaperShape.s.out_taper_max_value, 1)
                          : "--"
                }
                KeyLabel { text: "S端内塔" }
                ValueLabel {
                    text: root.alarmInfo.coreTaperShape.s.hasData
                          ? root.fmt(root.alarmInfo.coreTaperShape.s.in_taper_max_value, 1)
                          : "--"
                }
            }

            RowLayout {
                KeyLabel { text: "L端外塔" }
                ValueLabel {
                    text: root.alarmInfo.coreTaperShape.l.hasData
                          ? root.fmt(root.alarmInfo.coreTaperShape.l.out_taper_max_value, 1)
                          : "--"
                }
                KeyLabel { text: "L端内塔" }
                ValueLabel {
                    text: root.alarmInfo.coreTaperShape.l.hasData
                          ? root.fmt(root.alarmInfo.coreTaperShape.l.in_taper_max_value, 1)
                          : "--"
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 6

            RowLayout {
                spacing: 8
                Rectangle {
                    width: 10
                    height: 10
                    radius: 5
                    color: root.levelColor(root.flatLevel)
                }
                TitleLabel {
                    text: "扁卷信息"
                }
            }

            RowLayout {
                KeyLabel { text: "内径(mm)" }
                ValueLabel {
                    text: root.flatDiameterMm > 0 ? root.fmt(root.flatDiameterMm, 0) : "--"
                }
                KeyLabel { text: "等级" }
                ValueLabel { text: root.flatLevel > 0 ? String(root.flatLevel) : "--" }
            }

            RowLayout {
                KeyLabel { text: "S端内径" }
                ValueLabel {
                    text: root.alarmInfo.coreFlatRoll.s.hasData
                          ? root.fmt(root.alarmInfo.coreFlatRoll.s.innerDiameterMm, 0)
                          : "--"
                }
                KeyLabel { text: "L端内径" }
                ValueLabel {
                    text: root.alarmInfo.coreFlatRoll.l.hasData
                          ? root.fmt(root.alarmInfo.coreFlatRoll.l.innerDiameterMm, 0)
                          : "--"
                }
            }

            RowLayout {
                KeyLabel { text: "S端中心" }
                ValueLabel {
                    text: root.alarmInfo.coreFlatRoll.s.hasData
                          ? root.fmt(root.alarmInfo.coreFlatRoll.s.inner_circle_center_x, 0)
                            + "," + root.fmt(root.alarmInfo.coreFlatRoll.s.inner_circle_center_y, 0)
                          : "--"
                }
                KeyLabel { text: "L端中心" }
                ValueLabel {
                    text: root.alarmInfo.coreFlatRoll.l.hasData
                          ? root.fmt(root.alarmInfo.coreFlatRoll.l.inner_circle_center_x, 0)
                            + "," + root.fmt(root.alarmInfo.coreFlatRoll.l.inner_circle_center_y, 0)
                          : "--"
                }
            }

            RowLayout {
                KeyLabel { text: "S端旋转" }
                ValueLabel {
                    text: root.alarmInfo.coreFlatRoll.s.hasData
                          ? root.fmt(root.alarmInfo.coreFlatRoll.s.inner_circle_radius, 1)
                          : "--"
                }
                KeyLabel { text: "L端旋转" }
                ValueLabel {
                    text: root.alarmInfo.coreFlatRoll.l.hasData
                          ? root.fmt(root.alarmInfo.coreFlatRoll.l.inner_circle_radius, 1)
                          : "--"
                }
            }
        }
    }
}
