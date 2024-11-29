from . import *
from abc import ABC


class SurfaceConfig:
    pass

class PointABC(ABC):
    def __init__(self,*args):
        self.args=args

    def __iter__(self):
        return iter(self.args)

    def __getitem__(self, key):
        return self.args[key]

    def __repr__(self):
        return f"{self.__class__.__name__}({self.args})"

class Point2D(PointABC):
    def __init__(self, x, y, *args):
        super().__init__(*args)
        self.x=x
        self.y=y


class Point3D(PointABC):
    def __init__(self, x, y, z, *args):
        super().__init__(*args)
        self.x=x
        self.y=y
        self.z=z
