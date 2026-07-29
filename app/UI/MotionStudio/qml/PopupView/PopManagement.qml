import "../GlobalView"
Pops {// 在这
    id:root
    anchors.fill: parent
    GlobGlobErrorView{
        adaptiveMetrics: root.adaptiveMetrics
        style: root.appStyle
        modelStore: root.modelStore
    }  // 报警横幅
}
