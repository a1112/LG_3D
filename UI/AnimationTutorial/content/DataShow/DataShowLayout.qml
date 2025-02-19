import QtQuick
import QtQuick.Controls
import "_base_"
import "Core"
DataShowBackground {
    id: root

    property Binds binds_base:binds_s
    property Binds binds_s:Binds{
    surfaceData:coreModel.surfaceS
    }
    property Binds binds_l:Binds{
    surfaceData:coreModel.surfaceL
    }

    SplitView{
        anchors.fill: parent
        DataShowView{
            id: dataShowView_R
            surfaceData:coreModel.surfaceS
            dataShowCore : DataShowCore{
                surfaceData:coreModel.surfaceS
                binds:control.lockControl?binds_base:binds_s
            }
            SplitView.preferredWidth: root.is_half?root.viewWidth_half:root.viewWidth
        }

        DataShowView{
            surfaceData:coreModel.surfaceL
            dataShowCore : DataShowCore{
                surfaceData:coreModel.surfaceL
                binds:control.lockControl?binds_base:binds_l
            }
            id: dataShowView_L
            SplitView.preferredWidth : root.is_half?root.viewWidth_half:root.viewWidth
        }

    }

}

