pragma Singleton
import QtQuick.Studio.Application
import QtQuick 6.3


QtObject {
    enum ContType{
        RatateType=0,
        MoveType=1
    }
    property var currentType : ContCore.ContType.RatateType
    property int modelViewIndex: 0
    property var slider
    property bool showState: false
    property var startPoint: Qt.point(0,0)
    property var currentPoint: Qt.point(0,0)
    property var endPoint: Qt.point(0,0)
    property var rotatePoint: Qt.point(0,0)
    property var movePoint : Qt.point(0,0)
    function resetPoint(){
        rotatePoint = Qt.point(0,0)
        movePoint = Qt.point(0,0)
    }
    onCurrentPointChanged: {
        if (ContCore.currentType===ContCore.ContType.RatateType){
            rotatePoint=Qt.point(currentPoint.x-startPoint.x+endPoint.x,
                                 currentPoint.y-startPoint.y+endPoint.y)
        }
        else{
        movePoint=Qt.point(currentPoint.x-startPoint.x+endPoint.x,
                           currentPoint.y-startPoint.y+endPoint.y)
        }
    }
    property var eulerRotation: Qt.point(0,0)

    property ListModel historyTitleModel: ListModel{
        ListElement{
            title:"ID"
            key:"id_"
            wid:0.2
            fw:false
        }
        ListElement{
            title:"钢板号"
            key:"steelNo"
            wid:0.3
            fw:false
        }
        ListElement{
            title:"规格"
            key:"specification"
            wid:0.2
            fw:false
        }
        ListElement{
            title:"时间"
            key:"time_"
            wid:0.3
            fw:true
        }
    }

    property ListModel historyModel: ListModel{
        ListElement{
            id_:"1"
            steelNo:"test_no_1"
            specification:"10000 * 2000*12.5"
            time_:"2024-4-1 12:11"
        }
        ListElement{
            id_:"2"
            steelNo:"test_no_1"
            specification:"10000 * 2000*12.5"
            time_:"2024-4-1 12:11"
        }
    }
}
