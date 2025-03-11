import QtQuick

Item {
    property int coilId: 0  // 二级ID
    property int status:0
    property string msg:""
    function init(coilCheck){
                for (let i=0;i<coilCheck.count;i++ ){
                        let coilCheck_ =  coilCheck[i]
                        coilId = coilCheck_.secondaryCoilId
                        status = coilCheck_.status
                        msg = coilCheck_.msg
                }

    }
}
