import QtQuick
import "../../../../Model/server"
Item {
    property PointData pointData: PointData{}
    property var label_point:findPoint(p_x,p_y,type)
    PointItemPointShow{}
    PointItemLabelShow{}
    Component.onCompleted:{

        pointData.x_=p_x
        pointData.y_=p_y
        pointData.z_=p_z
        pointData.z_mm = z_mm
        pointData.id_=Id
        pointData.type_ = type
        pointData.secondaryCoilId_ = secondaryCoilId
        pointData.surface_=surface

    }
}
