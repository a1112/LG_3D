import QtQuick
import QtQuick.Layouts

import "Pages/Header"
import "Pages/Pop"

Item {
    id: root
    implicitWidth: adaptive.designWidth
    implicitHeight: adaptive.designHeight
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: coreStyle.appBackgroundColor
    }

    ColumnLayout {
        spacing: adaptive.mainSpacing
        anchors.fill: parent

        TopHeader {
        }

        StackLayout {
            currentIndex: app_core.appIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                asynchronous: true
                active: true
                source: "DataShowRoot.qml"
            }

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                asynchronous: true
                active: StackLayout.isCurrentItem || status === Loader.Ready
                source: "DefectShowRoot.qml"
            }
        }
    }

    LeftPrePop {
        id: lp
    }
}
