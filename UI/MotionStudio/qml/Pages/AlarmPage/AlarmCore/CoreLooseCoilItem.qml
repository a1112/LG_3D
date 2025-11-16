import QtQuick

Item {

    property string global_key:""

    property real max_width : 0.0
    property bool hasData:false

    function init(){
        hasData=false
        max_width=0
    }


    property var data
    onDataChanged:{
        if (data){
            hasData=true
            data.forEach((item)=>{
                             if (item.max_width>max_width){
                                 max_width=item.max_width
                             }
                         }
                         )
        }
        else{
            hasData=false
        }
    }
}
