import QtQuick

Item {

    property real innerDiameter: 0.0
    property real innerDiameterMm: -1.0
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
    innerDiameter=-1
    innerDiameterMm=-1
    alarmLevel=0
    l.init()
    s.init()
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
        innerDiameterMm=(l.innerDiameterMm+s.innerDiameterMm)/2
    }
    else if(l.hasData){
        innerDiameter=l.inner_circle_width
        innerDiameterMm=l.innerDiameterMm
    }
    else if (s.hasData){
        innerDiameter=s.inner_circle_width
        innerDiameterMm=s.innerDiameterMm
    }
    else{
        innerDiameter=-1
        innerDiameterMm=-1
    }
        if (innerDiameterMm>0){
                if (innerDiameterMm<680) {
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
