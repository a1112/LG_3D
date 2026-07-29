pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 卷列表的缺陷类别筛选器。
Item {
    id: root

    required property var leftController
    required property var globalContext
    required property var style

    readonly property var defectClasses: root.globalContext.defectClassProperty

    visible: root.leftController.fliterEnable
    width: parent ? parent.width : implicitWidth
    implicitHeight: flow.implicitHeight + 8
    SplitView.preferredHeight: root.visible ? Math.min(root.implicitHeight, 150) : 0
    clip: true

    function setAll(show) {
        let names = []
        for (let index = 0; index < root.defectClasses.defectDictModel.count; index++) {
            names.push(root.defectClasses.defectDictModel.get(index).name)
        }
        names.push(root.defectClasses.unDefectClassItemName)
        root.leftController.setListViewFilterClasses(names, show)
    }

    Flow {
        id: flow
        width: parent.width
        spacing: 4

        Repeater {
            model: root.defectClasses.defectDictModel

            delegate: CheckDelegate {
                id: classToggle
                required property string name

                implicitHeight: 32
                text: name

                Component.onCompleted:
                    checked = root.leftController.filterClassEnabled(name)

                Connections {
                    target: root.leftController
                    function onFliterDictChanged() {
                        classToggle.checked =
                                root.leftController.filterClassEnabled(classToggle.name)
                    }
                }

                onClicked:
                    root.leftController.setLiewViewFilterClass(name, checked)
            }
        }

        CheckDelegate {
            id: noDefectToggle
            implicitHeight: 32
            text: root.defectClasses.unDefectClassItemName

            Component.onCompleted:
                checked = root.leftController.filterClassEnabled(text)

            Connections {
                target: root.leftController
                function onFliterDictChanged() {
                    noDefectToggle.checked =
                            root.leftController.filterClassEnabled(noDefectToggle.text)
                }
            }

            onClicked:
                root.leftController.setLiewViewFilterClass(text, checked)
        }

        Button {
            implicitHeight: 32
            text: qsTr("全选")
            onClicked: root.setAll(true)
        }

        Button {
            implicitHeight: 32
            text: qsTr("取消")
            onClicked: root.setAll(false)
        }
    }
}
