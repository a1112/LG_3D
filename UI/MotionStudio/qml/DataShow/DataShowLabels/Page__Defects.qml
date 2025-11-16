import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    Layout.fillWidth: true
    height: column.height

    Column{
        id:column
    WarningInfo{
                visible:coreModel.toolDict["defect"]
    }
    FlatRollLabel{
        //平整度
        visible:coreModel.toolDict["defect"]
    }
    }
}
