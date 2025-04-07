import QtQuick
//  控制按钮
Item {
    property int app_index:app_core.appIndex
    onApp_indexChanged: flush_defects()

    property ListModel  currentListModel:  defectCoreModel.currentListModel

    function flush_defects(){
        api.getDefectsByCoilId(
                    defectCoreModel.currentListStartIndex,
                    defectCoreModel.currentListEndIndex,
                    (text)=>{
                        let  t = [
                            {"surface":"S","defectName":"边部褶皱",
                            "def ectStatus":0,"defectX":3250,"defectW":214,
                            "defectSource":0.839722,"secondaryCoilId":40864,
                            "Id":284530,"defectClass":1,
                            "defectTime":{"year":2024,"month":12,"weekday":0,"day":30,"hour":18,"minute":12,"second":21},"
                            defectY":5231,"defectH":99,"defectData":""}
                        ]
                        defectCoreModel.defectText = text
                    },
                    (err)=>{
                        console.log("")
                    }

                    )
    }
}
