import QtQuick

Rectangle {
    required property var style
    property bool active: false

    implicitWidth: 10
    implicitHeight: 10
    radius: width / 2
    color: active ? style.statusSuccessColor : style.statusErrorColor
}
