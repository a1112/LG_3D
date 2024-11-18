import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../Foot"
Popup{
    id: popup
    width: showViewListView.width+20
    height: showViewListView.height
    topMargin : 0
    leftMargin: 0
    bottomMargin: 0
    rightMargin: 0
    topPadding: 0
    leftPadding: 0
    bottomPadding: 0
    rightPadding: 0
    y: 30
    x: parent.width - width-30
    Material.elevation: 12

    ShowViewListView{
        id:showViewListView
        implicitHeight: 100
        width: 300
    }
    HoverHandler{
        id:hoverHandlerPop
    }
}
