import QtQuick.Controls

Menu {
    title:"标注"
    Menu{
        title:"塔形"
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


}