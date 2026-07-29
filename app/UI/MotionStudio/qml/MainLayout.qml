pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

import "Pages/Header"
import "Pages/Pop"

Item {
    id: root

    required property var adaptiveMetrics
    required property var style
    required property var model
    required property var settings
    required property var viewControl
    required property var appController
    required property var leftController

    implicitWidth: root.adaptiveMetrics.designWidth
    implicitHeight: root.adaptiveMetrics.designHeight
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: root.style.appBackgroundColor
    }

    ColumnLayout {
        spacing: root.adaptiveMetrics.mainSpacing
        anchors.fill: parent

        TopHeader {
        }

        StackLayout {
            currentIndex: root.appController.appIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                asynchronous: true
                active: true
                sourceComponent: DataShowRoot {
                    adaptiveMetrics: root.adaptiveMetrics
                    style: root.style
                    model: root.model
                    settings: root.settings
                    viewControl: root.viewControl
                }
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
        adaptiveMetrics: root.adaptiveMetrics
        style: root.style
        hoverController: root.leftController
    }
}
