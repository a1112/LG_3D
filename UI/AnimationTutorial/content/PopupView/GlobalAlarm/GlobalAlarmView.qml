import QtQuick 2.15
import "../../Pages/AlarmPage"
import "../../Pages/AlarmPage/AlarmItem"
import "../Base"
PopupBase {
    width:600
    height:bodyV.height+25
    Column{
        id:bodyV
        width: parent.width-10
        anchors.centerIn:parent
        AlarmItemCameras{
                    width: parent.width
            alarmLevel:coreModel.coreGlobalError.errorLevelDict["相机"]
            height: 100
        }
        AlarmItemNet{
                    width: parent.width
            height: 100
        }
        AlarmHardware{
                    width: parent.width

            height: 100
        }
    }
}
