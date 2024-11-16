import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../Labels"
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
