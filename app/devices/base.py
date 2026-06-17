"""Interface chung cho thiết bị. Logic chỉ gọi interface, không quan tâm mock/real."""
from abc import ABC, abstractmethod
from typing import Awaitable, Callable


class BaseScanner(ABC):
    """Máy quét mã. Gọi callback mỗi khi đọc được mã."""

    def __init__(self, on_scan: Callable[[str], Awaitable[None]]):
        self.on_scan = on_scan  # async func(ma_chai: str)

    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def stop(self): ...

    @abstractmethod
    async def is_connected(self) -> bool: ...


class BaseIOBox(ABC):
    """Điều khiển băng tải + cơ cấu đẩy loại chai."""

    @abstractmethod
    async def connect(self): ...

    @abstractmethod
    async def start_bang_tai(self): ...

    @abstractmethod
    async def stop_bang_tai(self): ...

    @abstractmethod
    async def day_loai_chai(self): ...

    @abstractmethod
    async def is_connected(self) -> bool: ...


class BaseLaser(ABC):
    """Máy in laser — khắc mã lên chai."""

    @abstractmethod
    async def connect(self): ...

    @abstractmethod
    async def print_code(self, ma_chai: str): ...

    @abstractmethod
    async def is_connected(self) -> bool: ...
