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
    required property var alarmInfo
    required property var apiClient
    required property var popupManager
    required property var authManager
    required property var globalContext
    required property var coreController

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
                adaptiveMetrics: root.adaptiveMetrics
                style: root.style
                modelStore: root.model
                authManager: root.authManager
                globalContext: root.globalContext
                coreController: root.coreController
                appController: root.appController
                viewControl: root.viewControl
                popupManager: root.popupManager
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
                    alarmInfo: root.alarmInfo
                    apiClient: root.apiClient
                    popupManager: root.popupManager
                    leftController: root.leftController
                    coreController: root.coreController
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
