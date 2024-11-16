import QtQuick 2.15

Item {


    property real tickSizeZ: 12
    property int tickCountZ: drawHeight/20
    property real medianZ: dataShowCore.medianZ
    onMedianZChanged:{
        surfaceData.medianZ = medianZ
    }


    property real offsetZ: 0
    property real dragOffsetZ: 0

    readonly property real minZ: offsetZ -(tickSizeZ * tickCountZ / 2)  + dragOffsetZ
    readonly property real maxZ:  offsetZ +(tickSizeZ * tickCountZ / 2)  + dragOffsetZ


    property real startDragX: 0
    property real startDragY: 0
    function startDrag(x,y){
        startDragX = x
        startDragY = y
    }

    function dragTo(x,y){
        var dx = (x - startDragX)*((tickSizeZ * tickCountZ)/drawWidth)
        var dy = (y - startDragY)*((tickSizeZ * tickCountZ)/drawWidth)
        dragOffsetZ = dy
    }
    function endDrag(){
        offsetZ += dragOffsetZ
        dragOffsetZ = 0
    }

    property var lineData: surfaceData.lineData

    function findZValue(arr, n) {
      let left = 0;
      let right = arr.length - 2;
      while (left <= right) {
        let mid = Math.floor((left + right) / 2);
        if (arr[mid][0] <= n && (mid + 1 >= arr.length || arr[mid + 1][0] > n)) {
          return arr[mid][2];
        } else if (arr[mid][0] >= n) {
          right = mid - 1;
        } else {
          left = mid + 1;
        }
      }
      return null; // 如果没有找到符合条件的值，返回 null
    }

    function getDistance(x1,y1){
        let i= 1
        if (x1 < surfaceData.inner_circle_centre[0])
        {
            i=-1
        }

        return Math.sqrt(Math.pow(x1-surfaceData.inner_circle_centre[0],2)+Math.pow(y1-surfaceData.inner_circle_centre[1],2))
        *surfaceData.scan3dScaleX*i
    }

    function isFilter(_list,i,n,value){
        for (var j = 1; j < n; j++) {
            if (i-j<0){
                continue
            }
            if (Math.abs(_list[i]-_list[i-j])>value){
                return true
            }
        }
        return false
    }
}
