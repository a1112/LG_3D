from abc import ABC
from enum import Flag, auto, Enum
from typing import Union, List


class BdItem:
    def __init__(self, bd_config):
        self.bdConfig = bd_config
        self.scan3dAxisMax = bd_config["Scan3dAxisMax"]
        self.scan3dAxisMin = bd_config["Scan3dAxisMin"]
        self.scan3dCoordinateOffset = bd_config["Scan3dCoordinateOffset"]
        self.scan3dCoordinateScale = bd_config["Scan3dCoordinateScale"]


class BdData:
    def __init__(self, bd_config):
        self.bdConfig = bd_config
        try:
            self.bdDataX = BdItem(bd_config["CoordinateA"])
            self.bdDataY = BdItem(bd_config["CoordinateB"])
            self.bdDataZ = BdItem(bd_config["CoordinateC"])
        except (BaseException,) as e:
            print(e)
            self.bdDataX = BdItem({
                "Scan3dAxisMax": 2559.0,
                "Scan3dAxisMin": 0.0,
                "Scan3dCoordinateOffset": -63.648475646972656,
                "Scan3dCoordinateScale": 0.33943653106689453
            })
            self.bdDataY = BdItem({
                "Scan3dAxisMax": 3.4028234663852886e+38,
                "Scan3dAxisMin": -3.4028234663852886e+38,
                "Scan3dCoordinateOffset": 0.0,
                "Scan3dCoordinateScale": 1.0
            })
            self.bdDataZ = BdItem({
                "Scan3dAxisMax": 65535.0,
                "Scan3dAxisMin": 1.0,
                "Scan3dCoordinateOffset": 3140.954345703125,
                "Scan3dCoordinateScale": 0.016115527600049973
            })


class PointABC(ABC):
    """Abstract base class for points."""
    def __init__(self, *args: Union[int, float]):
        self.args: List[Union[int, float]] = list(args)

    def __iter__(self):
        return iter(self.args)

    def __getitem__(self, key: int) -> Union[int, float]:
        return self.args[key]

    def __setitem__(self, key: int, value: Union[int, float]):
        self.args[key] = value

    def __repr__(self):
        return f"{self.__class__.__name__}({self.args})"


class Point2D(PointABC):
    """2D Point with x, y coordinates."""
    def __init__(self, x: Union[int, float] = 0, y: Union[int, float] = 0):
        super().__init__(x, y)

    @property
    def x(self) -> Union[int, float]:
        return self.args[0]

    @x.setter
    def x(self, value: Union[int, float]):
        self.args[0] = value

    @property
    def y(self) -> Union[int, float]:
        return self.args[1]

    @y.setter
    def y(self, value: Union[int, float]):
        self.args[1] = value


class Point3D(Point2D):
    """3D Point with x, y, z coordinates."""
    def __init__(self, x: Union[int, float] = 0, y: Union[int, float] = 0, z: Union[int, float] = 0):
        super().__init__(x, y)
        self.args.append(z)

    @property
    def z(self) -> Union[int, float]:
        return float(self.args[2])

    @z.setter
    def z(self, value: Union[int, float]):
        self.args[2] = value


class DetectionTaperShapeType(Flag):
    NONE = auto()
    WK_TYPE = auto()
    POINT_TYPE = auto()
    LINE_TYPE = auto()
    AREA_TYPE = auto()


class LevelingType(Flag):
    NONE = auto()
    WK_TYPE = auto()
    LinearRegression = auto()
    Config = auto()


class DetectionType(Flag):
    Detection = auto()
    DetectionAndClassifiers = auto()

class ImageType(Enum):
    GRAY = "GRAY"
    JET = "JET"
    MASK = "MASK"