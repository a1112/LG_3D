import QtQuick
import "../../Pages/AlarmPage"
import "../../Pages/AlarmPage/AlarmItem"
import "../Base"
PopupBase {
    id: root
    width: adaptive.boundedWidth(600, 440, 760)
    height: bodyV.height + adaptive.headerSideGap
    Column{
        id:bodyV
        width: parent.width - adaptive.mainSpacing
        anchors.centerIn:parent
        AlarmItemCameras{
                    width: parent.width
            alarmLevel:coreModel.coreGlobalError.errorLevelDict["相机"]
            height: adaptive.scaleMetric(100, 82, 130)
        }
        AlarmItemNet{
            width: parent.width
            pollingEnabled: root.opened
            height: adaptive.scaleMetric(100, 82, 130)
        }
        AlarmHardware{
                    width: parent.width

            height: adaptive.scaleMetric(100, 82, 130)
        }
    }
}
