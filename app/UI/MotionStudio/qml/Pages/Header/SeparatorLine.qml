import QtQuick

Rectangle{
    id: root

    required property var style

    color: root.style.accentColor
    width: 2
    height: parent ? Math.max(0, parent.height - 5) : 0
}
