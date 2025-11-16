import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts


Item {
    id:root
    property string global_key: ""
    property bool showMore: false
    height: coll.height
    property ListModel cameraModel: ListModel{
    }
    Frame{
        anchors.fill: parent
    }
    Column{
        id:coll
        width:parent.width
        Item{
            width:parent.width
            height:35
            RowLayout{
                anchors.fill: parent

                CheckDelegate{
                    implicitHeight:30
                    text: "渲染"
                    font.pointSize: 14
                    font.bold: true
                    scale:0.8

                }

                Item{
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }

                Label{

                    text:"塔形检测"
                    font.pointSize: 16
                    font.bold: true
                    color: Material.color(Material.Blue)
                    font.family: "Microsoft YaHei"
                }
                Item{
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
                ItemDelegate{
                    text: "180°▼"
                    font.family: "Material Icons"
                    implicitHeight:30
                    scale:0.8
                    onClicked:{
                        // menu_type.popup()
                    }
                    Rectangle{
                        border.color:Material.color(Material.Pink)
                        border.width: 1
                        color: "transparent"
                        anchors.fill: parent
                    }
                }
                Item{
                    width:2
                    Layout.fillHeight: true
                }
            }


        }


        TaperShapeAllShow{
            visible:coreAlarmInfo.coreTaperShape.s.hasData
            coreTaperShapeItem: coreAlarmInfo.coreTaperShape.s
        }
        TaperShapeAllShow{
            visible:coreAlarmInfo.coreTaperShape.l.hasData
            coreTaperShapeItem: coreAlarmInfo.coreTaperShape.l
        }
            Item{
                width:parent.width
                Layout.fillWidth: true
                height: 25
                ItemDelegate{
                    anchors.fill: parent
                    onClicked: {
                        showMore=!showMore
                    }
                    Label{
                        font.bold: true
                        anchors.centerIn: parent
                        text: showMore?"收起":"更多..."
                    }


                }

            }
        }

    }
