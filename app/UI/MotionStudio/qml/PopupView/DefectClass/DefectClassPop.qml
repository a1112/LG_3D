
import "../Base"
import "../../Labels"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
PopupBase {
    id:root
    width: adaptive.boundedWidth(500, 380, 640)
    height: adaptive.boundedHeight(500, 380, 680)

    function set_defect_dict_property(index,key,value){
        // let list_item = global.defectClassProperty.defectDictModel.get(index)
        // list_item[key]=value


        // global.defectClassProperty.defectDictModel.set(index,list_item)
        // console.log("set_defect_dict_property",index,key,value)
        let name_ = global.defectClassProperty.defectDictModel.get(index)["name"]
        // console.log(global.defectClassProperty.defectDictModel.get(index)["color"])
        // console.log("name_ ",name_)
        global.defectClassProperty.defectDictData[name_][key] = ""+value
        global.defectClassProperty.upDefectDictModelByDefectDictData()
    }


    Item{
        width:root.width
        height: root.height - adaptive.headerSideGap
        ColumnLayout{
            anchors.fill:parent
            TitleLabel{
                Layout.alignment:Qt.AlignHCenter
                text:qsTr("缺陷列表")
                color:Material.color(Material.Blue)
            }
            Item{
                id:list
                Layout.fillWidth:true
                Layout.fillHeight:true
                clip:true
                ListView{
                    anchors.fill:parent
                    model:global.defectClassProperty.defectDictModel
                    delegate:DefectClassShowItem{
                        width:list.width
                        height: adaptive.headerTabHeight
                    }
                }
            }
            RowLayout{
                Layout.fillWidth:true
                implicitHeight: adaptive.headerTabHeight
                spacing: adaptive.headerSideGap
                Item{
                    Layout.fillWidth:true
                    implicitHeight: adaptive.headerTabHeight
                }
                Button{
                    text:qsTr("保存 ")
                    onClicked:{
                        // let data = tool.list_model_to_json(global.defectClassProperty.defectDictModel)
                        let data = global.defectClassProperty.defectDictData
                        console.log(JSON.stringify(data))
                        api.setDefecctClassConfig(data)
                    }
                }
                Button{
                    text:"添加 "
                    onClicked:{
                    }
                }
            }
        }
    }
}
