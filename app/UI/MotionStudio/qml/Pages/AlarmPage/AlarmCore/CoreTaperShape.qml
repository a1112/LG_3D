import QtQuick

Item {


    readonly property real innerTaper: Math.max(l.innerTaperValue, s.innerTaperValue)
    readonly property real outTaper: Math.max(l.outTaperValue, s.outTaperValue)
    readonly property int alarmLevel: Math.max(l.level, s.level, outTaper > 75 || innerTaper > 10 ? 3 : (l.hasData || s.hasData ? 1 : 0))
    property string str:l.str+"\n\n"+s.str
    property ListModel taperErrorList: ListModel{
    }


    property var data
    property CoreTaperShapeItem l: CoreTaperShapeItem{
        global_key:"L\n端"
    }
    property CoreTaperShapeItem s: CoreTaperShapeItem{
        global_key:"S\n端"
    }
    onDataChanged:{
    taperErrorList.clear()
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
