import QtQuick
MsgBgBase {
    id:root
    height: flow.height
    Flow{
        width: parent.width
        id:flow
        Repeater{
            model: defectViewState.selectCountModel
         DefectInfoItem{
        }
        }
    }

}
