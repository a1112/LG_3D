import QtQuick

Item {

    property real innerDiameter: 0.0
    property int alarmLevel: 0
    property bool hasData: false
    property var data

    property CoreFlatRollItem l: CoreFlatRollItem{
        global_key:"L\n端"
    }
    property CoreFlatRollItem s: CoreFlatRollItem{
        global_key:"S\n端"
    }
    onDataChanged:{
    hasData=false
    l.hasData=false
    s.hasData=false
    for (let key in data){
        if (key=="L"){
            l.data=data[key]
            hasData=true
        }
        else{
            s.data=data[key]
            hasData=true
        }
    }


    if(l.hasData && s.hasData){
        innerDiameter=(l.inner_circle_width+s.inner_circle_width)/2
    }
    else if(l.hasData){
        innerDiameter=l.inner_circle_width.toFixed(2)
    }
    else if (s.hasData){
        innerDiameter=s.inner_circle_width.toFixed(2)
    }
    else{
        innerDiameter=-1
    }
        if (innerDiameter>0){
                if (innerDiameter<680) {
                    alarmLevel=2
                }
                else{
                alarmLevel=1
                }
        }
        else{
            alarmLevel=0

        }
    }


}
