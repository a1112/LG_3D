import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../CardBase"

SplitView{

    CardBaseView {

            SplitView.fillWidth: true
            SplitView.fillHeight: true
            card_id:"defectViewL"
        }

    CardBaseView {

        SplitView.fillWidth: true
        SplitView.fillHeight: true
        card_id:"defectViewR"
    }

}
