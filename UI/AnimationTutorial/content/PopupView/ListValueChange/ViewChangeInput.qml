import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Labels"
import "../../Input"
Item {
    Layout.fillWidth:true
    height:35

    function init(){
        var listModel = coreModel.currentCoilListModel
        let l = listModel.get(0).Id
        let r = listModel.get(listModel.count-1).Id
        start_input_id.text=r
        end_input_id.text=l
        api.getCoilListValueChangeKeys((result)=>{
                                       let data_json = JSON.parse(result)
                                       cb.model = data_json

                                       },(err)=>{


                                       })
    }

    RowLayout{
        anchors.fill:parent
        KeyLabel{
            text:"数值类型： "
        }
        ComboBox{
            id:cb
            model:[]
            implicitHeight: 30
            implicitWidth:200
            onCurrentTextChanged:{
            }
        }

        KeyLabel{
            text:"起始值 ："
        }
        TextFieldBase{
            id:start_input_id

        }
        KeyLabel{
            text:"结束值 ："
        }
        TextFieldBase{
            id:end_input_id
        }
        Button{
            text:"刷新"
            implicitHeight: 30
            onClicked:{


            }
        }
    }
}
