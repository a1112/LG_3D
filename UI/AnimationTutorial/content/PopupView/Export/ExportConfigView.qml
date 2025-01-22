import QtQuick
import QtQuick.Controls

Item {
    Flow{
            anchors.fill:parent
            CheckDelegate{

                    id: tx
                    height:25
                    text: qsTr("3D检测信息")
                    checked:true
            }
            CheckDelegate{
                    id: df
                    height:25
                    text: qsTr("缺陷信息")
                    checked:true
            }
            CheckDelegate{
                    id: df_v
                    height:25
                    text: qsTr("缺陷检出")
                    checked:true
            }
            CheckDelegate{
                    id: df_su_v
                    height:25
                    text: qsTr("屏蔽")
                    checked:false
            }
    }


    function getExportConfig(){
        return {
            export_type:"xlsx",
            detection_3d_info:tx.checked
            // detection_defect_info
        }
    }
}
