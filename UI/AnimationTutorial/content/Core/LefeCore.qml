import QtQuick
import "../Model"
Item {
    property int hovedCoilId: 0
    property bool searchViewShow: true

    property string leftMsg:""



    onSearchViewShowChanged: {
        if (! searchViewShow){
            coreModel.currentCoilListIndex = 0
        }
    }
    property var hovelCoilData:{return {}}
    property int searchPageIndex   : 0
    onHovedCoilIdChanged: {

        preSourceModelS.setProperty(0,"image_source",coreModel.surfaceS.getSource(hovedCoilId,"GRAY",true))
        preSourceModelS.setProperty(1,"image_source",coreModel.surfaceS.getSource(hovedCoilId,"JET",true))
        preSourceModelL.setProperty(0,"image_source",coreModel.surfaceL.getSource(hovedCoilId,"GRAY",true))
        preSourceModelL.setProperty(1,"image_source",coreModel.surfaceL.getSource(hovedCoilId,"JET",true))
    }

    property int hovedIndex:-1

    property  CoilModel hovedCoilModel

    onHovedIndexChanged: {
        let p = coreModel.currentCoilListModel.get(hovedIndex)
        hovelCoilData=p
        hovedCoilId = p.SecondaryCoilId
    }

    property bool isHoved:false
    property point hoverPoint: Qt.point(0,0)

    property ListModel preSourceModelS: ListModel{
        ListElement{
            key:"GRAY"
            image_source:""
        }
        ListElement{
            key:"JET"
            image_source:""
        }

    }
    property ListModel preSourceModelL: ListModel{
        ListElement{
            key:"GRAY"
            image_source:""
        }
        ListElement{
            key:"JET"
            image_source:""
        }

    }

}
