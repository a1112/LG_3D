import QtQuick
import "../Pages/View3D"
Loader{
    active: surfaceData.is3DrootView
    sourceComponent: View3DRoot{

    }
}
