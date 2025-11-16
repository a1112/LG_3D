import QtQuick
/*
  界面管理


*/
import "GraphsValueView"
GraphsValueViewMain{
  property GraphsCore graphsCore: GraphsCore{}

  function open(){
    visible=true
    graphsCore.init()

  }

}
