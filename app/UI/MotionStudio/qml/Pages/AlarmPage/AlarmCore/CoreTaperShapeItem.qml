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
    readonly property real outTaperValue: Math.max(Math.abs(out_taper_max_value), Math.abs(out_taper_min_value))
    readonly property real innerTaperValue: Math.max(Math.abs(in_taper_max_value), Math.abs(in_taper_min_value))

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
    property bool hasData:false

    function numberValue(value, defaultValue) {
        if (value === undefined || value === null) {
            return defaultValue
        }
        let numberValue_ = Number(value)
        return isFinite(numberValue_) ? numberValue_ : defaultValue
    }

    function taperScore(item, keys) {
        let score = 0
        for (let i = 0; i < keys.length; i++) {
            score = Math.max(score, Math.abs(numberValue(item[keys[i]], 0)))
        }
        return score
    }

    function init() {
        hasData=false
        out_taper_max_x=0
        out_taper_max_y=0
        out_taper_max_value=0
        out_taper_min_x=0
        out_taper_min_y=0
        out_taper_min_value=0
        in_taper_max_x=0
        in_taper_max_y=0
        in_taper_max_value=0
        in_taper_min_x=0
        in_taper_min_y=0
        in_taper_min_value=0
        rotation_angle=0
        level=0
        err_msg=""
    }

    function applyOutItem(item) {
        out_taper_max_x=numberValue(item["out_taper_max_x"], 0)
        out_taper_max_y=numberValue(item["out_taper_max_y"], 0)
        out_taper_max_value=numberValue(item["out_taper_max_value"], 0)
        out_taper_min_x=numberValue(item["out_taper_min_x"], 0)
        out_taper_min_y=numberValue(item["out_taper_min_y"], 0)
        out_taper_min_value=numberValue(item["out_taper_min_value"], 0)
    }

    function applyInItem(item) {
        in_taper_max_x=numberValue(item["in_taper_max_x"], 0)
        in_taper_max_y=numberValue(item["in_taper_max_y"], 0)
        in_taper_max_value=numberValue(item["in_taper_max_value"], 0)
        in_taper_min_x=numberValue(item["in_taper_min_x"], 0)
        in_taper_min_y=numberValue(item["in_taper_min_y"], 0)
        in_taper_min_value=numberValue(item["in_taper_min_value"], 0)
    }

    onDataChanged:{
        init()
        if (!data || data.length <= 0){
            return
        }

        hasData=true
        var outItem=data[0]
        var inItem=data[0]
        var metaItem=data[0]
        var outScore=-1
        var inScore=-1
        var metaScore=-1

        data.forEach((item)=>{
            let currentOutScore = taperScore(item, ["out_taper_max_value", "out_taper_min_value"])
            let currentInScore = taperScore(item, ["in_taper_max_value", "in_taper_min_value"])
            let currentMetaScore = Math.max(currentOutScore, currentInScore)
            if (currentOutScore > outScore) {
                outScore = currentOutScore
                outItem = item
            }
            if (currentInScore > inScore) {
                inScore = currentInScore
                inItem = item
            }
            if (currentMetaScore > metaScore) {
                metaScore = currentMetaScore
                metaItem = item
            }
        })

        applyOutItem(outItem)
        applyInItem(inItem)
        rotation_angle=numberValue(metaItem["rotation_angle"], 0)
        level=numberValue(metaItem["level"], 0)
        err_msg=metaItem["err_msg"] || ""
    }



}
