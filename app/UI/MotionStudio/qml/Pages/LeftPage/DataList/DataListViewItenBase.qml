import QtQuick
import "Core"
import "../../../Model"

Item {
    id: root

    required property int index
    required property var model
    required property var style
    required property var coreController
    required property var modelController
    required property var leftController
    required property var popupManager
    required property var apiClient
    required property var globalContext

    width: 300
    height: 30
    readonly property bool isCurrentIndex: coilModel.coilId > 0
                                                   && coilModel.coilId === coreController.currentCoilModel.coilId

    property CoilModel coilModel: CoilModel {
        globalContext: root.globalContext
        apiClient: root.apiClient
    }
    property ListItemCoil listItemCoil: ListItemCoil {
        style: root.style
        hasCoil: root.coilModel.hasCoil
        alarmInfo: root.coilModel.coilData ? root.coilModel.coilData.AlarmInfo : null
        maxDefectName: root.coilModel.maxDefectName || ""
        maxDefectLevel: root.coilModel.maxDefectLevel || 0
        maxDefectSurface: root.coilModel.maxDefectSurface || ""
    }

    function syncModel() {
        if (model && model.Id !== undefined) {
            coilModel.init(model)
        }
    }

    onIndexChanged: syncModel()
    ListView.onReused: syncModel()
    Component.onCompleted: syncModel()

    Rectangle {
        anchors.fill: parent
        radius: root.style.controlRadius
        color: root.isCurrentIndex
               ? root.style.selectionColor
               : hoverHandler.hovered
                 ? root.style.buttonHoverColor
                 : index % 2 === 0
                   ? root.style.panelAlternateColor
                   : root.style.panelElevatedColor
        border.width: root.isCurrentIndex ? 1 : 0
        border.color: root.style.accentColor
    }

    Rectangle {
        width: root.isCurrentIndex ? 4 : 2
        height: parent.height
        anchors.left: parent.left
        color: root.isCurrentIndex ? root.style.accentColor : "transparent"
        radius: 2
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: {
            if (root.leftController.selectVisibleIndex(root.index)) {
                root.modelController.setKeepLatest(false)
            }
        }
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: root.popupManager.popupDataListItemMenu(root.coilModel)
    }

    HoverHandler {
        id: hoverHandler
        onHoveredChanged: {
            if (hovered) {
                root.leftController.hovedIndex = root.index
            } else if (root.leftController.hovedIndex === root.index) {
                root.leftController.hovedIndex = -1
            }
        }
    }
}
