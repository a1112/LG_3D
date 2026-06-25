import QtQuick

import QtQuick.Controls.Material
import "AlarmCore"
Item {
    property int coilId: core.currentCoilModel.coilId
    readonly property bool hasAlarm: alarmLevel>1
    property int alarmLevel: Math.max(coreFlatRoll.alarmLevel, coreTaperShape.alarmLevel, coreLooseCoil.alarmLevel)
    readonly property color alarmColor: alarmLevel<=1?Material.color(Material.Green):alarmLevel<=2?Material.color(Material.Yellow):Material.color(Material.Red)


    property var flatRollData: coilAlarmData["FlatRoll"] || ({})

    property CoreFlatRoll coreFlatRoll: CoreFlatRoll{
                data:coilAlarmData["FlatRoll"] || ({})
    }

    property CoreTaperShape coreTaperShape:CoreTaperShape{
                data:coilAlarmData["TaperShape"] || ({})
    }


    property CoreLooseCoil coreLooseCoil:CoreLooseCoil{
                data:coilAlarmData["LooseCoil"] || ({})
    }

    property var coilAlarmData: ({})

    onCoilIdChanged:{
        api.getCoilAlarm(coilId,(data)=>{
                             try {
                                 coilAlarmData=JSON.parse(data)
                             } catch (e) {
                                 console.log("getCoilAlarm parse error", e)
                                 coilAlarmData = {}
                             }
                             if(coilAlarmData["FlatRoll"]){
                                 coreModel.coreGlobalError.setError(2001,false)
                             }
                             else{
                                coreModel.coreGlobalError.setError(2001,true)
                             }
                         },(err)=>{

                         })

    }


}
