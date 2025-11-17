import QtQuick 2.15

Item {
    property var coilStateData: []

    property int median_3d: 0
    property real median_3d_mm: 0
    property real scan3dCoordinateScaleX: 0
    property real scan3dCoordinateScaleY: 0
    property real scan3dCoordinateScaleZ: 0

    readonly property bool flatRollWarning: x_y_scale>1.1 || x_y_scale<0.9
    readonly property bool lowerAreaWarning: lowerArea_percent>0.02
    readonly property bool upperAreaWarning: upperArea_percent>0.02

    property real x_y_scale: 1.0

    property real lowerArea_percent: 0

    property real upperArea_percent: 0

    function load(){
        coilStateData.forEach(
                (data,index)=>{
                        x_y_scale = data["width"]/data["height"]
                        median_3d = data["median_3d"]
                        median_3d_mm = data["median_3d_mm"]
                        lowerArea_percent = data["lowerArea_percent"]
                        upperArea_percent = data["upperArea_percent"]
                        scan3dCoordinateScaleX = data["scan3dCoordinateScaleX"]
                        scan3dCoordinateScaleY = data["scan3dCoordinateScaleY"]
                        scan3dCoordinateScaleZ = data["scan3dCoordinateScaleZ"]

            }
        )
    }
    Component.onCompleted:{
        api.getCoilState(Id,(result)=>{
                             // [{"scan3dCoordinateScaleX":0.339437,"colorFromValue_mm":-20.0,"lowerArea_percent":0.00707693,
                             //      "scan3dCoordinateScaleY":1.0,"colorToValue_mm":20.0,"upperArea_percent":3.6634e-05,
                             //      "Id":307,"scan3dCoordinateScaleZ":0.0161155,"start":46595.4,"mask_area":25249781,
                             //      "rotate":-90,"step":2483.0,"width":6995,"secondaryCoilId":1868,
                             //      "x_rotate":10,"upperLimit":6205.2,"height":5180,"median_3d":47837.4,
                             //      "lowerLimit":-3102.6,
                             //      "jsonData":"{'coilId': '1868', 'direction': 'R', 'startTime': datetime.datetime(2024, 8, 16, 17, 28, 54, 517439), 'scan3dCoordinateScaleX': 0.33943653106689453, 'scan3dCoordinateScaleY': 1.0, 'scan3dCoordinateScaleZ': 0.016115527600049973, 'crossPoints': [(2275, 63), (2362, 359)], 'rotate': -90, 'crop_box': (1, 1538, 6995, 5180), 'x_rotate': 10, 'median_3d': 47837.397452758094, 'median_3d_mm': 770.9248989644833, 'colorFromValue_mm': -20, 'colorToValue_mm': 20, 'start': 46595.397452758094, 'step': 2483.0, 'upperLimit': 6205.19554070882, 'lowerLimit': -3102.59777035441, 'lowerArea': 178691, 'upperArea': 925, 'lowerArea_percent': 0.00707693266725759, 'upperArea_percent': 3.663398110264798e-05, 'mask_area': 25249781, 'width': 6995, 'height': 5180, 'circleConfig': {'inner_circle': {'circlex': [3521, 2971, 1337], 'ellipse': ((3527.085693359375, 2853.949462890625), (1946.699951171875, 2614.9560546875), 89.48193359375), 'inner_circle': [(3521.5, 2852.0), 986.0]}}}",
                             //      "surface":"R","median_3d_mm":null,"lowerArea":178691,
                             //      "startTime":{"year":2024,"month":8,"weekday":4,"day":16,"hour":17,"minute":28,"second":55},
                             //      "upperArea":925},

                             //    {"scan3dCoordinateScaleX":0.339437,"colorFromValue_mm":-20.0,
                             //      "lowerArea_percent":0.00812553,"scan3dCoordinateScaleY":1.0,"colorToValue_mm":20.0,
                             //      "upperArea_percent":0.000164062,"Id":306,"scan3dCoordinateScaleZ":0.0161155,"start":54211.2,
                             //      "mask_area":25715871,"rotate":90,"step":2483.0,"width":7024,"secondaryCoilId":1868,
                             //      "x_rotate":17,"upperLimit":6205.2,"height":5336,"median_3d":55453.2,
                             //      "lowerLimit":-3102.6,
                             //      "jsonData":"{'coilId': '1868', 'direction': 'L', 'startTime': datetime.datetime(2024, 8, 16, 17, 28, 54, 608487), 'scan3dCoordinateScaleX': 0.33943653106689453, 'scan3dCoordinateScaleY': 1.0, 'scan3dCoordinateScaleZ': 0.016115527600049973, 'crossPoints': [(2236, 188), (2068, 377)], 'rotate': 90, 'crop_box': (4164, 1401, 7024, 5336), 'x_rotate': 17, 'median_3d': 55453.21641044834, 'median_3d_mm': 893.6578395741243, 'colorFromValue_mm': -20, 'colorToValue_mm': 20, 'start': 54211.21641044834, 'step': 2483.0, 'upperLimit': 6205.19554070882, 'lowerLimit': -3102.59777035441, 'lowerArea': 208955, 'upperArea': 4219, 'lowerArea_percent': 0.00812552683904815, 'upperArea_percent': 0.00016406210779327678, 'mask_area': 25715871, 'width': 7024, 'height': 5336, 'circleConfig': {'inner_circle': {'circlex': [3557, 2940, 1386], 'ellipse': ((3520.43310546875, 2854.49365234375), (2177.34033203125, 2689.84375), 83.79122924804688), 'inner_circle': [(3568.13720703125, 2891.76513671875), 1122.9912109375]}}}",
                             //      "surface":"L","median_3d_mm":null,"lowerArea":208955,"startTime":{"year":2024,"month":8,
                             //      "weekday":4,"day":16,"hour":17,"minute":28,"second":55},"upperArea":4219}]
                            coilStateData=JSON.parse(result)
                             load()
                         },
                         (error)=>{
                             console.log("getCoilState error",error)
                         }
            )
    }
}
