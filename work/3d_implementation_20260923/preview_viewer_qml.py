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
model_scale_value = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
model_scale = [model_scale_value] * 3
width, height = 1200, 700
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
    width: 1200; height: 700
    QtObject { id: surface
        property string key: "S"
        property string meshUrl: "MODEL_URL"
        property bool meshExits: true
        property string meshBuildState: ""
        property var coilInfo: ({width: 2000})
        signal meshReloadRequested()
    }
    QtObject { id: stubControls; property real scaleZ: 0.5; property bool isRotateModel: false; property bool isMoveModel: false }
    QtObject { id: stubDataCore; property var controls3D: stubControls }
    QtObject { id: stubController
        property real cameraOffsetX: 0; property real cameraOffsetY: 0; property real cameraOffsetZ: 0
        property real objectOffsetX: 0; property real objectOffsetY: 0; property real objectOffsetZ: 0
        property vector3d objectScale: Qt.vector3d(MODEL_SCALE)
    }
    QtObject { id: stubStyle; property color viewportBackgroundColor: "#10202c"; property color headerBorderColor: "#34505e" }
    Production.View3DRoot { id: viewer; objectName: "viewer"; anchors.fill: parent
        surfaceData: surface; dataShowCore: stubDataCore; view3DController: stubController; style: stubStyle
    }
}
""".replace("NODE_URL", node_dir).replace("MODEL_URL", model.as_uri()).replace("MODEL_SCALE", ",".join(map(str, model_scale)))
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
    viewer = item.findChild(QObject, "viewer")
    ready = viewer.property("frontModelReady")
    width_mm = float(viewer.property("frontModelWidth") or 0)
    height_mm = float(viewer.property("frontModelHeight") or 0)
    image = fbo.toImage()
    rgb_image = image.convertToFormat(QImage.Format_RGBA8888)
    pixels = np.frombuffer(rgb_image.constBits(), dtype=np.uint8).reshape(height, rgb_image.bytesPerLine())
    rgb = pixels[:, :width * 4].reshape(height, width, 4)[:, :, :3]
    # The skybox is blue; the imported material is neutral gray. Crop labels at top.
    viewport = rgb[100:].astype(np.int16)
    gray_geometry = ((np.max(viewport, axis=-1) - np.min(viewport, axis=-1)) < 25) & (np.mean(viewport, axis=-1) > 80)
    half = width // 2
    left_pixels = int(np.count_nonzero(gray_geometry[:, :half]))
    right_pixels = int(np.count_nonzero(gray_geometry[:, half:]))
    result = {
        "ready": ready,
        "size": [width_mm, height_mm],
        "native": model.suffix.lower() == ".mesh",
        "error": viewer.property("frontLoadError"),
        "render_method": "QQuickRenderControl / OpenGL framebuffer",
        "frames": frame_count,
        "initial_camera_distance": viewer.property("initialCameraDistance"),
        "initial_camera_fit_applied": viewer.property("initialCameraFitApplied"),
        "surface_spacing_mm": viewer.property("surfaceSpacingMm"),
        "model_display_width": viewer.property("modelDisplayWidth"),
        "left_gray_geometry_pixels": left_pixels,
        "right_gray_geometry_pixels": right_pixels,
        "both_halves_have_geometry_pixels": left_pixels > 100 and right_pixels > 100,
        "window_visible": window.isVisible(),
        "window_exposed": window.isExposed(),
        "model": str(model),
    }
    result["model_scale"] = model_scale
    result["image_saved"] = image.save(str(output))
    result["image_size"] = [image.width(), image.height()]
    output.with_suffix('.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    code = 0 if (ready and width_mm > 0 and height_mm > 0 and result["image_saved"]
                 and result["both_halves_have_geometry_pixels"]) else 1
    control.invalidate()
    app.exit(code)


timer = QTimer()
timer.setInterval(16)
timer.timeout.connect(render_frame)
timer.start()
raise SystemExit(app.exec())
