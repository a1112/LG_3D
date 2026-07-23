import QtQuick
import ProcessObj 1.0
import Clipboard 1.0
Item {
    ProcessObj{
        id:pro
    }
    Clipboard{
        id:clip
    }
    function system(cmd){
        return pro.system_(cmd)
    }
    function setText(text){
        return clip.setText(text)
    }
}
