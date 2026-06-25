import QtQuick

Item {


    property real innerTaper:0.0
    property real outTaper:0.0
    readonly property int alarmLevel: max_width > 25 ? 3 : (l.hasData || s.hasData ? 1 : 0)

    readonly property real max_width : Math.max(l.max_width, s.max_width)

    property ListModel errorList: ListModel{
    }


    property var data
    property CoreLooseCoilItem l: CoreLooseCoilItem{
        global_key:"L\n端"
        scaleX: coreModel.surfaceL.scan3dScaleX
        scaleY: coreModel.surfaceL.scan3dScaleY
    }
    property CoreLooseCoilItem s: CoreLooseCoilItem{
        global_key:"S\n端"
        scaleX: coreModel.surfaceS.scan3dScaleX
        scaleY: coreModel.surfaceS.scan3dScaleY
    }
    onDataChanged:{
    errorList.clear()
    l.init()
    s.init()
    for (let key in data){
        if (key=="L"){
            l.data=data[key]
        }
        else{
            s.data=data[key]
        }
    }
    }
}
