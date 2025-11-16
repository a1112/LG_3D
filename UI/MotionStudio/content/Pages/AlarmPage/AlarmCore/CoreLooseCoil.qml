import QtQuick

Item {


    property real innerTaper:0.0
    property real outTaper:0.0
    property int alarmLevel: 0

    readonly property real max_width : Math.min(l.max_width, s.max_width)

    property ListModel errorList: ListModel{
    }


    property var data
    property CoreLooseCoilItem l: CoreLooseCoilItem{
        global_key:"L\n端"
    }
    property CoreLooseCoilItem s: CoreLooseCoilItem{
        global_key:"S\n端"
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
