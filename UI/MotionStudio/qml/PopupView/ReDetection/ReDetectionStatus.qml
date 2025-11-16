import QtQuick

Item {

        property int stuteNone:0
        property int stuteRuuing:1
        property int stuteFinished:2
        property int stuteError:3

        property int currentStatus:stuteNone

        property real progress:0.0


        readonly property bool isNone:currentStatus==stuteNone

        readonly property bool isRuuing:currentStatus==stuteRuuing

        readonly property bool isError:currentStatus==stuteError

        readonly property bool isFinished:currentStatus==stuteFinished

        property string errorStr:""

        property bool canChange:isNone

        function strat(){
            currentStatus=stuteRuuing
            progress=0.0
        }

        function setRunning(){
            currentStatus=stuteRuuing
        }

        function setError(errorStr){
            currentStatus=stuteError
            this.errorStr=errorStr
        }

        function setFinished(){
            currentStatus=stuteFinished
        }

        function setNone(){
            currentStatus=stuteNone
        }
}
