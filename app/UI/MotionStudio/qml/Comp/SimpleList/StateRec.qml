import QtQuick 2.15
import QtQuick.Controls 2.15
Rectangle {
    property int steelState: 0
    radius: width
    height: parent.height
    width: height
    color:{
        if (steelState==0)
            return "yello"
        else if(steelState==2)
        return "green"
        return "red"
    }
}
