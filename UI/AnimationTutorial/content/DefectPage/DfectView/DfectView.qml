import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

SplitView{
    id:root
    // CardBaseView {
    //         SplitView.fillHeight: true
    //         SplitView.preferredWidth: root.width/2-2
    //         card_id:"defectViewL"
    //     }

    CardBaseView {
        defectCoreModel:defectViewCore.defectCoreModel
        SplitView.fillWidth: true
        SplitView.fillHeight: true
        card_id:"defectViewR"
    }

}
