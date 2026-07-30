import QtQuick
/*
  界面管理


*/
import "GraphsValueView"
GraphsValueViewMain{
  id: root

  required property var modelStore

  graphController: graphsCore

  property GraphsCore graphsCore: GraphsCore {
    modelStore: root.modelStore
  }

  function open(){
    root.visible = true
    root.graphsCore.init()

  }

}
