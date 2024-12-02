from abc import ABC
from typing import List, Union


class SurfaceConfig:
    """Placeholder for surface configuration."""
    pass


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
        return self.args[2]

    @z.setter
    def z(self, value: Union[int, float]):
        self.args[2] = value

