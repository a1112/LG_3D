import QtQuick

Item {

    property string global_key: ""
    property var data

    property int out_taper_max_x: 0
    property int out_taper_max_y: 0
    property real out_taper_max_value: 0.0
    property int out_taper_min_x: 0
    property int out_taper_min_y: 0
    property real out_taper_min_value: 0.0

    property int in_taper_max_x: 0
    property int in_taper_max_y: 0
    property real in_taper_max_value: 0.0
    property int in_taper_min_x: 0
    property int in_taper_min_y: 0
    property real in_taper_min_value: 0.0

    property real rotation_angle: 0.0

    property string str:
        " :"+global_key+
        "\n外塔\n"+
        " x:"+out_taper_max_x+
        "  y:"+out_taper_max_y+
        "  value:"+out_taper_max_value+
        "\n内塔\n"+
        " x:"+in_taper_max_x+
        " y:"+in_taper_max_y+
        " value:"+in_taper_max_value+
        "\n"+
        " rotation:"+rotation_angle

    // out_taper_max_x = Column(Integer)
    // out_taper_max_y = Column(Integer)
    // out_taper_max_value = Column(Float)
    // out_taper_min_x = Column(Integer)
    // out_taper_min_y = Column(Integer)
    // out_taper_min_value = Column(Float)

    // in_taper_max_x = Column(Integer)
    // in_taper_max_y = Column(Integer)
    // in_taper_max_value = Column(Float)
    // in_taper_min_x = Column(Integer)
    // in_taper_min_y = Column(Integer)
    // in_taper_min_value = Column(Float)

    // rotation_angle = Column(Float)

    property var level: 0
    property var err_msg: ""
    property bool hasData:true

    onDataChanged:{
        if (data.length>0){
[{"Id":19,"in_taper_max_x":2050,
                "err_msg":null,"surface":"L","in_taper_max_y":0,"crateTime":{"year":2024,"month":10,"weekday":0,"day":21,"hour":17,"minute":37,"second":26},
                "out_taper_max_x":482,"in_taper_max_value":34.804,
                "data":null,"out_taper_max_y":0,"in_taper_min_x":1670,"out_taper_max_value":4.69725,
                "in_taper_min_y":0,"out_taper_min_x":37,"in_taper_min_value":-5.09497,"out_taper_min_y":0,
                "rotation_angle":180,"secondaryCoilId":1755,"out_taper_min_value":-8.20563,"level":null},
            {"Id":20,"in_taper_max_x":4202,"err_msg":null,"surface":"L","in_taper_max_y":0,
                "crateTime":{"year":2024,"month":10,"weekday":0,"day":21,"hour":17,"minute":37,"second":26},
                "out_taper_max_x":5636,"in_taper_max_value":33.0899,"data":null,"out_taper_max_y":0,
                "in_taper_min_x":4541,"out_taper_max_value":1.25331,"in_taper_min_y":0,"out_taper_min_x":6212,"in_taper_min_value":-8.7611,
                "out_taper_min_y":0,"rotation_angle":0,"secondaryCoilId":1755,"out_taper_min_value":-22.1401,"level":null}]
            hasData=true
            var data_=data[0]
            out_taper_max_x=data_["out_taper_max_x"]
            out_taper_max_y=data_["out_taper_max_y"]
            out_taper_max_value=data_["out_taper_max_value"]
            out_taper_min_x=data_["out_taper_min_x"]
            out_taper_min_y=data_["out_taper_min_y"]
            out_taper_min_value=data_["out_taper_min_value"]

            if (out_taper_max_value>outTaper){
                outTaper=out_taper_max_value
            }

            in_taper_max_x=data_["in_taper_max_x"]
            in_taper_max_y=data_["in_taper_max_y"]
            in_taper_max_value=data_["in_taper_max_value"]
            in_taper_min_x=data_["in_taper_min_x"]
            in_taper_min_y=data_["in_taper_min_y"]
            in_taper_min_value=data_["in_taper_min_value"]
            if (in_taper_max_value>innerTaper){
                innerTaper=in_taper_max_value
            }

            rotation_angle=data_["rotation_angle"]
            level=data_["level"]
            err_msg=data_["err_msg"]
        }
        else{
            hasData=false
        }

    }



}
