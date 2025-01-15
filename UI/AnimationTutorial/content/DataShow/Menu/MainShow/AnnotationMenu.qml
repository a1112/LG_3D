import QtQuick.Controls
import "../../../Controls/Menu"
Menu {
    title: "显示"
    Menu{
        title:"塔形标注"
        Menu{
            title:"显示类型"
            MenuItem{
                text:"外塔 + 溢出"
            }
            MenuItem{
                text:"外塔 - 溢出"
            }
            MenuItem{
                text:"内塔 + 溢出"
            }
            MenuItem{
                text:"内塔 - 溢出"
            }
        }
        Menu{
            title:"显示密度"
            MenuItem{
                text:"自动"
            }
            MenuItem{
                text:"低密度 12 点"
            }

            MenuItem{
                text:"高密度 72 点"
            }

        }


    }

    Menu{
        title: "缺陷显示"
        Menu{
            title : "缺陷标签"
                SelectMenuItem{
                    text: "显示"
                    selectd:global.defectClassProperty.defeftDrawShowLasbel
                    onClicked:global.defectClassProperty.defeftDrawShowLasbel=true
                }
                SelectMenuItem{
                    text: "隐藏"
                     selectd:!global.defectClassProperty.defeftDrawShowLasbel
                    onClicked:global.defectClassProperty.defeftDrawShowLasbel=false
                }
        }
    }
}
