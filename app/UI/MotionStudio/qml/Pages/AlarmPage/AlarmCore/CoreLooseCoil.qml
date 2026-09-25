import QtQuick

Item {
    id: root

    required property var modelStore

    property real innerTaper:0.0
    property real outTaper:0.0
    readonly property int alarmLevel: max_width > 25 ? 3 : (l.hasData || s.hasData ? 1 : 0)

    readonly property real max_width : Math.max(l.max_width, s.max_width)

    property ListModel errorList: ListModel{
    }


    property var data
    property CoreLooseCoilItem l: CoreLooseCoilItem{
        global_key:"L\n端"
        scaleX: root.modelStore.surfaceL.scan3dScaleX
        scaleY: root.modelStore.surfaceL.scan3dScaleY
    }
    property CoreLooseCoilItem s: CoreLooseCoilItem{
        global_key:"S\n端"
        scaleX: root.modelStore.surfaceS.scan3dScaleX
        scaleY: root.modelStore.surfaceS.scan3dScaleY
    }
    onDataChanged:{
    root.errorList.clear()
    root.l.init()
    root.s.init()
    for (let key in root.data){
        if (key=="L"){
            root.l.data = root.data[key]
        }
        else{
            root.s.data = root.data[key]
        }
    }
    }
}
