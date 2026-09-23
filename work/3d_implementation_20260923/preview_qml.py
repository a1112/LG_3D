"""Render the production QML 3D component without exposing a desktop window."""
import json
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "windows"
os.environ["QT_QUICK_BACKEND"] = "rhi"
os.environ["QSG_RHI_BACKEND"] = "opengl"
os.environ["QSG_RENDER_LOOP"] = "basic"

from PySide6.QtCore import QTimer, QUrl, QObject, QSize
from PySide6.QtGui import QGuiApplication, QImage, QOpenGLContext, QOffscreenSurface, QSurfaceFormat
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtQuick import (QQuickWindow, QQuickRenderControl, QQuickRenderTarget,
                             QQuickGraphicsDevice, QSGRendererInterface)
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
import numpy as np

root = Path(__file__).resolve().parents[2]
model = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
rotation_y = float(sys.argv[3]) if len(sys.argv) > 3 else 0
model_scale = [float(value) for value in sys.argv[4].split(",")] if len(sys.argv) > 4 else [1, 1, 1]
model_offset = [float(value) for value in sys.argv[5].split(",")] if len(sys.argv) > 5 else [0, 0, 0]
width, height = 1000, 640
app = QGuiApplication([])
QQuickWindow.setGraphicsApi(QSGRendererInterface.OpenGL)

surface_format = QSurfaceFormat()
surface_format.setDepthBufferSize(24)
surface_format.setStencilBufferSize(8)
context = QOpenGLContext()
context.setFormat(surface_format)
if not context.create():
    raise SystemExit("OpenGL context creation failed")
surface = QOffscreenSurface()
surface.setFormat(context.format())
surface.create()
if not context.makeCurrent(surface):
    raise SystemExit("Offscreen OpenGL context activation failed")

control = QQuickRenderControl()
window = QQuickWindow(control)
window.setGeometry(0, 0, width, height)
window.setGraphicsDevice(QQuickGraphicsDevice.fromOpenGLContext(context))
if not control.initialize():
    raise SystemExit("QQuickRenderControl initialization failed")
fbo_format = QOpenGLFramebufferObjectFormat()
fbo_format.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
fbo = QOpenGLFramebufferObject(QSize(width, height), fbo_format)
if not fbo.isValid():
    raise SystemExit("OpenGL framebuffer allocation failed")
target = QQuickRenderTarget.fromOpenGLTexture(fbo.texture(), QSize(width, height))
window.setRenderTarget(target)

engine = QQmlEngine()
component = QQmlComponent(engine)
node_dir = (root / "app/UI/MotionStudio/qml/DataShow/View3D").as_uri()
qml = """
import QtQuick
import QtQuick3D
import "NODE_URL" as Production
Item {
    width: 1000; height: 640
    QtObject { id: surface; property string key: "S"; property string meshUrl: "MODEL_URL"; signal meshReloadRequested() }
    View3D {
        anchors.fill: parent
        camera: viewCamera
        environment: SceneEnvironment { backgroundMode: SceneEnvironment.Color; clearColor: "#10202c"; antialiasingMode: SceneEnvironment.MSAA }
        PerspectiveCamera { id: viewCamera; z: 530; clipFar: 2000 }
        DirectionalLight { eulerRotation.x: -20; eulerRotation.y: -30; brightness: 0.85 }
        DirectionalLight { eulerRotation.y: 170; brightness: 0.25 }
        Node {
            eulerRotation.x: -28; eulerRotation.y: -15
            Production.Node3D {
                objectName: "testedModel"; surfaceData: surface; modelRotationY: ROTATION_Y
                modelScale: Qt.vector3d(MODEL_SCALE)
                modelOffsetX: OFFSET_X; modelOffsetY: OFFSET_Y; modelOffsetZ: OFFSET_Z
            }
        }
    }
    Text { x: 28; y: 24; color: "white"; font.family: "Arial"; font.pixelSize: 24; text: "Synthetic 3D reconstruction / FORMAT" }
    Text { x: 28; y: 60; color: "#afc5d3"; font.family: "Arial"; font.pixelSize: 16; text: "Calibrated millimetres · preserved eye and missing-data hole" }
}
""".replace("NODE_URL", node_dir).replace("MODEL_URL", model.as_uri()).replace("FORMAT", model.suffix).replace("ROTATION_Y", str(rotation_y)).replace("MODEL_SCALE", ",".join(map(str, model_scale))).replace("OFFSET_X", str(model_offset[0])).replace("OFFSET_Y", str(model_offset[1])).replace("OFFSET_Z", str(model_offset[2]))
component.setData(qml.encode(), QUrl.fromLocalFile(str(output.with_suffix('.qml'))))
item = component.create()
if item is None:
    raise SystemExit("QML failed to create: " + "\n".join(error.toString() for error in component.errors()))
item.setParentItem(window.contentItem())
frame_count = 0


def render_frame():
    global frame_count
    context.makeCurrent(surface)
    control.polishItems()
    control.beginFrame()
    control.sync()
    control.render()
    control.endFrame()
    context.functions().glFinish()
    frame_count += 1
    if frame_count >= 90:
        timer.stop()
        verify()


def verify():
    node = item.findChild(QObject, "testedModel")
    ready = node.property("modelReady")
    size = node.property("modelSize")
    center_expression = QQmlExpression(QQmlEngine.contextForObject(node), node, """
    (function() {
        let midpoint = Qt.vector3d((modelBoundsMin.x + modelBoundsMax.x) / 2,
                                  (modelBoundsMin.y + modelBoundsMax.y) / 2,
                                  (modelBoundsMin.z + modelBoundsMax.z) / 2);
        for (let index = 0; index < children.length; ++index) {
            if (children[index].objectName === "3D.obj")
                return children[index].mapPositionToNode(children[index].parent, midpoint);
        }
        return Qt.vector3d(999, 999, 999);
    })()
    """)
    effective_center, _ = center_expression.evaluate()
    if center_expression.hasError():
        print(center_expression.error().toString(), flush=True)
    result = {
        "ready": ready,
        "size": [size.x(), size.y(), size.z()],
        "native": node.property("nativeMeshSource"),
        "error": node.property("loadError"),
        "render_method": "QQuickRenderControl / OpenGL framebuffer",
        "frames": frame_count,
        "rotation_y": rotation_y,
        "effective_center": [effective_center.x(), effective_center.y(), effective_center.z()] if effective_center is not None else None,
        "window_visible": window.isVisible(),
        "window_exposed": window.isExposed(),
        "model": str(model),
    }
    for property_name in ("modelBoundsMin", "modelBoundsMax", "autoCenterOffset"):
        vector = node.property(property_name)
        result[property_name] = [vector.x(), vector.y(), vector.z()]
    image = fbo.toImage()
    rgb_image = image.convertToFormat(QImage.Format_RGBA8888)
    pixels = np.frombuffer(rgb_image.constBits(), dtype=np.uint8).reshape(height, rgb_image.bytesPerLine())
    rgb = pixels[:, :width * 4].reshape(height, width, 4)[:, :, :3]
    difference = np.max(np.abs(rgb[100:].astype(np.int16) - rgb[100, 0].astype(np.int16)), axis=-1)
    result["model_pixel_count"] = int(np.count_nonzero(difference > 10))
    result["model_scale"] = model_scale
    result["model_offset"] = model_offset
    result["centering_error_mm"] = (float(np.linalg.norm(np.asarray(result["effective_center"]) - model_offset))
                                    if effective_center is not None else None)
    result["image_saved"] = image.save(str(output))
    result["image_size"] = [image.width(), image.height()]
    output.with_suffix('.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    code = 0 if (ready and size.x() > 0 and size.y() > 0 and result["image_saved"]
                 and result["model_pixel_count"] > 1000 and result["centering_error_mm"] is not None
                 and result["centering_error_mm"] < 0.001) else 1
    control.invalidate()
    app.exit(code)


timer = QTimer()
timer.setInterval(16)
timer.timeout.connect(render_frame)
timer.start()
raise SystemExit(app.exec())
