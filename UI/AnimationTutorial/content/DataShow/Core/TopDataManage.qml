import QtQuick

QtObject {

    readonly property int lineShowModel: 2  // 线段的显示方式
    readonly property int dataInfoShowModel: 1  // 数据显示方式
    readonly property int defectShowModel: 0  // 缺陷显示方式

    property int currentShowModel: lineShowModel

}
