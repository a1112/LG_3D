import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../btns/iconBtns"
import "../../Labels"
Row {
    height:parent.height
    spacing:10
    KeyLabel{
        anchors.verticalCenter: parent.verticalCenter
        text:"工具:"
    }
    MoveIconBtn{
        selected:dataShowCore.controls.isMoveModel
        onClicked: {
            dataShowCore.controls.currentMouseModel=dataShowCore.controls.mouseMoveModel
        }
    }
    SurveyIconBtn{
        selected: dataShowCore.controls.isShowSurveyModel
        onClicked: {
            dataShowCore.controls.currentMouseModel=dataShowCore.controls.mouseSurveyModel
        }

    }


}
