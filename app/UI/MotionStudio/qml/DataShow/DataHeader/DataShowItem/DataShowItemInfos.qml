import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Base"
import "../../DataShowLabels/Base"

DataShowItemBase {
    id: root

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

    property real taperOut: coreAlarmInfo.coreTaperShape.outTaper
    property real taperIn: coreAlarmInfo.coreTaperShape.innerTaper
    property int taperLevel: Math.max(taperOut > 75 ? 3 : 1, taperIn > 10 ? 3 : 1)

    property real flatDiameterRaw: coreAlarmInfo.coreFlatRoll.innerDiameter
    property real flatDiameterMm: flatDiameterRaw > 0 ? flatDiameterRaw * coreModel.surfaceS.scan3dScaleX : -1
    property int flatLevel: flatDiameterMm > 0 && flatDiameterMm < 680 ? 2 : flatDiameterMm > 0 ? 1 : 0

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
                    color: levelColor(taperLevel)
                }
                TitleLabel {
                    text: "塔形报警"
                }
            }

            RowLayout {
                KeyLabel { text: "外塔(mm)" }
                ValueLabel { text: fmt(taperOut, 1) }
                KeyLabel { text: "内塔(mm)" }
                ValueLabel { text: fmt(taperIn, 1) }
            }

            RowLayout {
                KeyLabel { text: "S端外塔" }
                ValueLabel {
                    text: coreAlarmInfo.coreTaperShape.s.hasData
                          ? fmt(coreAlarmInfo.coreTaperShape.s.out_taper_max_value, 1)
                          : "--"
                }
                KeyLabel { text: "S端内塔" }
                ValueLabel {
                    text: coreAlarmInfo.coreTaperShape.s.hasData
                          ? fmt(coreAlarmInfo.coreTaperShape.s.in_taper_max_value, 1)
                          : "--"
                }
            }

            RowLayout {
                KeyLabel { text: "L端外塔" }
                ValueLabel {
                    text: coreAlarmInfo.coreTaperShape.l.hasData
                          ? fmt(coreAlarmInfo.coreTaperShape.l.out_taper_max_value, 1)
                          : "--"
                }
                KeyLabel { text: "L端内塔" }
                ValueLabel {
                    text: coreAlarmInfo.coreTaperShape.l.hasData
                          ? fmt(coreAlarmInfo.coreTaperShape.l.in_taper_max_value, 1)
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
                    color: levelColor(flatLevel)
                }
                TitleLabel {
                    text: "扁卷信息"
                }
            }

            RowLayout {
                KeyLabel { text: "内径(mm)" }
                ValueLabel { text: flatDiameterMm > 0 ? fmt(flatDiameterMm, 0) : "--" }
                KeyLabel { text: "等级" }
                ValueLabel { text: flatLevel > 0 ? String(flatLevel) : "--" }
            }

            RowLayout {
                KeyLabel { text: "S端内径" }
                ValueLabel {
                    text: coreAlarmInfo.coreFlatRoll.s.hasData
                          ? fmt(coreAlarmInfo.coreFlatRoll.s.inner_circle_width * coreModel.surfaceS.scan3dScaleX, 0)
                          : "--"
                }
                KeyLabel { text: "L端内径" }
                ValueLabel {
                    text: coreAlarmInfo.coreFlatRoll.l.hasData
                          ? fmt(coreAlarmInfo.coreFlatRoll.l.inner_circle_width * coreModel.surfaceL.scan3dScaleX, 0)
                          : "--"
                }
            }

            RowLayout {
                KeyLabel { text: "S端中心" }
                ValueLabel {
                    text: coreAlarmInfo.coreFlatRoll.s.hasData
                          ? fmt(coreAlarmInfo.coreFlatRoll.s.inner_circle_center_x, 0) + "," + fmt(coreAlarmInfo.coreFlatRoll.s.inner_circle_center_y, 0)
                          : "--"
                }
                KeyLabel { text: "L端中心" }
                ValueLabel {
                    text: coreAlarmInfo.coreFlatRoll.l.hasData
                          ? fmt(coreAlarmInfo.coreFlatRoll.l.inner_circle_center_x, 0) + "," + fmt(coreAlarmInfo.coreFlatRoll.l.inner_circle_center_y, 0)
                          : "--"
                }
            }

            RowLayout {
                KeyLabel { text: "S端旋转" }
                ValueLabel {
                    text: coreAlarmInfo.coreFlatRoll.s.hasData
                          ? fmt(coreAlarmInfo.coreFlatRoll.s.inner_circle_radius, 1)
                          : "--"
                }
                KeyLabel { text: "L端旋转" }
                ValueLabel {
                    text: coreAlarmInfo.coreFlatRoll.l.hasData
                          ? fmt(coreAlarmInfo.coreFlatRoll.l.inner_circle_radius, 1)
                          : "--"
                }
            }
        }
    }
}
