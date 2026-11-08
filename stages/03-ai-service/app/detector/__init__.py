"""检测器实现集合。

这里只导出抽象与数据类，不在包级导入 mamba_yolo：
它依赖 ultralytics / numpy / opencv，占位模式不应因此加载重依赖。
需要真实实现时按名显式导入：from .detector.mamba_yolo import MambaYoloDetector
"""

from .base import Detection, Detector, Frame

__all__ = ["Detection", "Detector", "Frame"]
