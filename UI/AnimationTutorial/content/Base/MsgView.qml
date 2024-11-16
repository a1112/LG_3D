import QtQuick 2.15
import QtQuick.Controls 2.15
import "../Base"
import "../Labels"
import QtQuick.Layouts 1.15

    MsgBgBase {
        height:1*dpi
        width:1*dpi

    ColumnLayout{
         width: parent.width
        id:col
            TitleLabel{
                color:"#fff"
                text: control.getNameById(defectItemData.defectID)
                Layout.alignment: Qt.AlignHCenter
        }
            TitleLabel{
                color:"#fff"
                text: "相机号: "+defectItemData.cameraId+" "+"索引: "+defectItemData.imageIndex+" 缺陷ID: "+defectItemData.defectID
                Layout.alignment: Qt.AlignHCenter
        }
                    TitleLabel{
                        color:"#fff"
                        text: "缺陷等级: "+defectItemData.grade
                        Layout.alignment: Qt.AlignHCenter
                }
                TitleLabel{
                    color:"#fff"
                    text: "距头: "+defectItemData.topInImg/1000 +" m"
                    Layout.alignment: Qt.AlignHCenter
                }
                TitleLabel{
                    color:"#fff"
                    text: "距边: "+defectItemData.leftInImg/1000 +" m  "+defectItemData.rightInImg/1000 +" m"
                    Layout.alignment: Qt.AlignHCenter
                }
                TitleLabel{
                    color:"#fff"
                    text: "置信度: "+defectItemData.defectCoefficient
                    Layout.alignment: Qt.AlignHCenter
            }
    }

}
