import QtQuick
import "../"
QtObject {
    property var data
    property int id_:0
    property int secondaryCoilId_:0
    property string surface_:""
    property string type_:""
    property real x_:0
    property real y_:0
    property real z_:0
    property real z_mm:0
    property DateTimeProject crateTime_:DateTimeProject{}
    property var allTypes : ["user","min_inner","max_inner","min_outer","max_outer"]


    property var defaultPoint: {
        "type": "user",
        "secondaryCoilId": 35858,
        "Id": 337249,
        "x": 4012,
        "y": 2891,
        "z_mm": -39.1953,
        "crateTime": {
            "year": 2024,
            "month": 12,
            "weekday": 4,
            "day": 13,
            "hour": 14,
            "minute": 39,
            "second": 15
        },
        "surface": "L",
        "z": 30435,
        "data": null
    }
}
