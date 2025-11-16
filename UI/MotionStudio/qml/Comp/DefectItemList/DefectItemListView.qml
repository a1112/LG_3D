import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import "../../Base"
RowLayout{
    anchors.fill: parent
    spacing: 5
    property alias model: listView.model
    Item{
        width: dpi*0.2
    }
    Item{
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        ListView{
            id:listView
            spacing: 15
            anchors.fill: parent
            orientation:ListView.Horizontal
            delegate:
                Item{
                height: raw.height
                width: dpi*1.2
                ItemDelegate{
                    HoverHandler{//缺陷列表
                        cursorShape:Qt.PointingHandCursor
                        onHoveredChanged: {
                            if(hovered){
                                sdm.openDefectListDialogView(coreModels.defectListDialogDict[code])
                            }
                            else{
                                sdm.closeDefectListDialogView()
                            }

                        }
                    }
                    anchors.fill: parent
                    onClicked: {
                        var temp=coreModels.defectShowDict
                        temp[code]=temp[code]??true?false:true
                        coreModels.defectShowDict=temp
                    }
                }
                Row{
                    id:raw
                    spacing: 0.1*dpi
                    CheckRec{
                        onClicked: {
                            var temp=coreModels.defectShowDict
                            temp[code]=temp[code]??true?false:true
                            coreModels.defectShowDict=temp
                        }
                        //                        mouseEnabled:false
                        //                        bgColor:"#9C9C9C"
                        showColor: show_color
                        height: width
                        checked: coreModels.defectShowDict[code]??true
                    }
                    Column{
                        LabelBase{
                            font.bold: true
                            text: code+" "+defectName+"   "
                        }
                        LabelBase{
                            text: "上表:"+upCount+"个"
                        }
                        LabelBase{
                            text: "下表:"+downCount+"个"
                        }
                    }
                }
            }
            ScrollBar.horizontal:ScrollBar{
                height: 0.08*dpi
//                policy :ScrollBar.AlwaysOn
            }
        }
    }
    Column{
        Layout.alignment: Qt.AlignTop
        spacing:5
        CheckRec{
            showColor:"red"
            show_text: "全选"
            Layout.alignment: Qt.AlignTop
            onCheckedChanged: {
                if (checked){
                    //全选
                    control.defectAllIn()
                }
                else{
                    // 取消全选
                    control.defectAllOut()
                }

            }
        }
        CheckRec{
            show_text: "周期缺陷"
            Layout.alignment: Qt.AlignTop
        }
    }
    Item{
        width: dpi*0.5
    }
}

