import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id:root
    property string category
//    property alias category: sett.category
    property alias font: lab.font
    property string name:""
    Label{
        id:lab
        font.family: "宋体"
    }
    property bool kerning: lab.font.kerning
    property alias family: lab.font.family
    property alias bold: lab.font.bold
    property alias italic: lab.font.italic
    property alias underline: lab.font.underline
    property alias pointSize: lab.font.pointSize
//    property alias pixelSize: lab.font.pixelSize
    property alias overline: lab.font.overline
    property alias strikeout: lab.font.strikeout
//    SettingsBase{
//        id:sett
//        property alias family: root.family
//        property alias kerning: root.kerning
//        property alias bold: root.bold
//        property alias italic: root.italic
//        property alias underline: root.underline
//        property alias pointSize: root.pointSize
////        property alias pixelSize: root.pixelSize
//        property alias overline: root.overline
//        property alias strikeout: root.strikeout
//    }
}
