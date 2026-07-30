import QtQuick
import "AlarmCore"
import "../../Core/JsonUtils.js" as JsonUtils
Item {
    id: root

    required property var coreController
    required property var apiClient
    required property var modelStore
    required property var style

    property int coilId: root.coreController.currentCoilModel.coilId
    property int requestGeneration: 0
    readonly property bool hasAlarm: alarmLevel>1
    property int alarmLevel: Math.max(coreFlatRoll.alarmLevel, coreTaperShape.alarmLevel, coreLooseCoil.alarmLevel)
    readonly property color alarmColor: alarmLevel <= 1
                                        ? root.style.statusSuccessColor
                                        : alarmLevel <= 2
                                          ? root.style.statusWarningColor
                                          : root.style.statusErrorColor


    property var flatRollData: coilAlarmData["FlatRoll"] || ({})

    property CoreFlatRoll coreFlatRoll: CoreFlatRoll{
                data: root.coilAlarmData["FlatRoll"] || ({})
    }

    property CoreTaperShape coreTaperShape:CoreTaperShape{
                data: root.coilAlarmData["TaperShape"] || ({})
    }


    property CoreLooseCoil coreLooseCoil:CoreLooseCoil{
                data: root.coilAlarmData["LooseCoil"] || ({})
                modelStore: root.modelStore
    }

    property var coilAlarmData: ({})

    onCoilIdChanged: {
        root.requestGeneration += 1
        let generation = root.requestGeneration
        let requestedCoilId = root.coilId
        if (requestedCoilId <= 0) {
            root.coilAlarmData = {}
            return
        }
        root.apiClient.getCoilAlarm(requestedCoilId, function(data) {
            if (generation !== root.requestGeneration
                    || requestedCoilId !== root.coilId) {
                return
            }
            root.coilAlarmData = JsonUtils.parse(data, {}, "coil alarm")
            root.modelStore.coreGlobalError.setError(
                        2001, !root.coilAlarmData["FlatRoll"])
        }, function() {
            if (generation === root.requestGeneration
                    && requestedCoilId === root.coilId) {
                root.coilAlarmData = {}
                root.modelStore.coreGlobalError.setError(2001, true)
            }
        })
    }


}
