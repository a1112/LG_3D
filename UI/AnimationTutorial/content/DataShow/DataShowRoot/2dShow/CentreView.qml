import QtQuick 2.15

Item {

    Rectangle{
        color: "red"
        width: 2
        x:-width/2
        height: 10
        y: -height/2
    }
    Rectangle{
        color: "red"
        width: 10
        height: 2
        y:-height/2
        x: -width/2
    }


}
