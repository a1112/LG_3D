import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Layouts
Item{
Canvas {
        id: gridCanvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            var cellSize = 15;
            for (var x = 0; x < width; x += cellSize) {
                for (var y = 0; y < height; y += cellSize) {
                    ctx.fillStyle = ((x / cellSize + y / cellSize) % 2 === 0) ?"rgba(255, 255, 255, 0)" : coreStyle.backC;
                    ctx.fillRect(x, y, cellSize, cellSize);
                }
            }
        }
    }
}
