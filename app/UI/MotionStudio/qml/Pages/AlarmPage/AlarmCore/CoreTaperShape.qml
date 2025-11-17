import QtQuick

Item {


    property real innerTaper:0.0
    property real outTaper:0.0
    property int alarmLevel: 0
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
    l.hasData=false
    s.hasData=false
    innerTaper=0.0
    outTaper=0.0

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
