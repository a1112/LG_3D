import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    width:200
    height:200

    Item{
        width: parent.width-6
        height: parent.height-6
        anchors.centerIn: parent
        Pane{
            anchors.fill: parent
            Material.elevation: 5
        }
        ColumnLayout{
    anchors.fill: parent
            Item{
                Layout.fillHeight: true
                Layout.fillWidth: true
                Image{
                    anchors.centerIn: parent
                width: parent.width
                height: parent.height
                asynchronous:true
                fillMode: Image.PreserveAspectFit
                source: api.defect_url(dataShowCore.coilId,dataShowCore.key,
                                       dataShowCore.currentViewKey,
                                       defectX,defectY,defectW,defectH
                                       )
            }
            }
    DefectInfos{

    }


    }
    }
    }

