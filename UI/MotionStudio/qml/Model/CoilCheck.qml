import QtQuick

Item {
    property var coilCheck
    property int coilId: 0  // 二级ID
    property color statusColor:
                status==0?"#00000000":status==2?"red":"green"
    property int status:0
            /*
                0：   未标注
                1：   通过
                2：   回退

            */

    function setStatus(status_){
        status = status_
        coilCheck.status = status_
    }
    function setMsg(msg_){
        msg = msg_
        coilCheck.msg = msg
    }

    property string msg:""
    function init(coilCheck_){
        if (undefined == coilCheck_){
            return
        }
        tool.for_list_model(coilCheck_,(coilCheck__)=>{
                                coilCheck = coilCheck__
                                coilId = coilCheck__.secondaryCoilId
                                status = coilCheck__.status
                                 msg = coilCheck__.msg
                            })

                // for (let i=0;i<coilCheck_.count;i++ ){
                //     coilCheck = coilCheck_.get()
                //         let coilCheck__ =  c[i]
                //     console.log(c)
                //         coilId = coilCheck__.secondaryCoilId
                //         status = coilCheck__.status
                //         msg = coilCheck__.msg
                //             console.log("coilCheck",coilCheck__.secondaryCoilId)
                // }

    }
}
