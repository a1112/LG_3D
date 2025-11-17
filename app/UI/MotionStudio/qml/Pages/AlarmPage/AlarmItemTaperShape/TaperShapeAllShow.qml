import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material

import "../AlarmCore"
import "../AlarmSimple"
Item {
 property CoreTaperShapeItem coreTaperShapeItem
    id:root
    width:parent.width
    height:col.height


    Frame{
        anchors.fill: parent
    }
    Row{
        id:row
        width:parent.width
        spacing: 10
        Label{
            id:titleLabel
            text:coreTaperShapeItem.global_key
            font.pointSize: 14
            font.bold: true
            color: Material.color(Material.Yellow)
            font.family: "Microsoft YaHei"
            anchors.verticalCenter: col.verticalCenter
        }
        Column{
            id:col
            width:root.width-titleLabel.width
            // SimpleValueRow{
            //     width:col.width
            //     title:"检测角度"
            //     value:coreTaperShapeItem.rotation_angle
            //     height: 30
            // }
            SimpleValueRow{
                width:col.width
                height: 30
                title:"外塔形最高"
                value:coreTaperShapeItem.out_taper_max_value.toFixed(1)
            }
            SimpleValueRow{
                width:col.width
                height: 30
                title:"外塔形最低"
                value:coreTaperShapeItem.out_taper_min_value.toFixed(1)
            }
            SimpleValueRow{
                width:col.width
                height: 30
                title:"内塔形最高"
                value:coreTaperShapeItem.in_taper_max_value.toFixed(1)
            }
            SimpleValueRow{
                width:col.width
                height: 30
                title:"内塔形最低"
                value:coreTaperShapeItem.in_taper_min_value.toFixed(1)
            }

        }
    }



}
