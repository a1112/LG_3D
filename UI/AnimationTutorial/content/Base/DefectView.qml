import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
Item{
    id:root
    onHeightChanged:coreState.defectViewDrawHeight=height
    onWidthChanged: coreState.defectViewDrawWidth=width
    Flickable {
        clip:true
        anchors.fill: parent
        id:flick
        focus: true
        interactive: false
        contentX:coreState.activeImShowStartIndexChangeAnim? coreState.imShowStartIndex*item_width:coreState.showStartX
        onContentXChanged: {
            coreState.showStartX=contentX
            if (contentX<0 ||contentX>contentWidth-root.width)
                return
            if (Math.abs(contentX/item_width-coreState.imShowStartIndex)>0.1)
                coreState.imShowStartIndex=contentX/item_width
        }
        property real imCanShowCount: width/item_width
        onImCanShowCountChanged: {
            coreState.imCanShowCount=imCanShowCount
        }
        contentWidth: imageCount*item_width
        contentHeight: steelDrawWidth //defectShowViewroot.steelDrawHeight

        Repeater{
            model: imageCount
            Rectangle{
                width: 5
                height: 5
                x:index*item_width
                Label{
                    text: index
                    anchors.top: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }
        Rectangle{
            visible: otherImageModel
            border.width: 3
            border.color:Material.color(Material.BlueGrey)
            x:selectDefectObj.imageIndex*item_width
            y:((selectDefectObj.cameraId-1)%cameraListMiodel.count)*item_height
            width:item_width
            color: "#00000000"
            height: item_height
            Behavior on x{
                NumberAnimation{duration: 400}
            }
            Behavior on y{
                NumberAnimation{duration: 400}
            }
        }
        //        contentWidth: steelDrawWidth//defectShowViewroot.steelDrawWidth
        DefectDraw{
            width: imageCount*item_width//defectShowViewroot.steelDrawWidth //
            height:root.height
            id:contentView
            x:0
        }
        SelectCursor{   // 选择指针
            visible: otherImageModel
        }
        ScrollBar.horizontal:scr
    }
    SelectItemInfoView{
        //        height: 1.2*dpi
        visible: contentView.selectCanView
        width: defectViewState.selectRec.width-defectViewState.selectRec.x
        x:defectViewState.selectRec.x-flick.contentX+contentView.x
        y:defectViewState.selectRec.y-height
    }
    ScrollBar{
        anchors.top: flick.bottom
        id:scr
        width: flick.width
        height: 0.1*dpi
        policy :ScrollBar.AlwaysOn
        onActiveChanged: {
            if(active){
                coreState.activeImShowStartIndexChangeAnim=false
            }
            else
                coreState.activeImShowStartIndexChangeAnim=true
        }
    }
}
