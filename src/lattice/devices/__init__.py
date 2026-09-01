from .pressure_gauge import PressureGauge
from .shutter import Shutter
from .source import Source
from .motor import Motor
from .substrate_motor import SubstrateMotor
from .loading_motor import LoadingMotor
from .camera import Camera
from .device_manager import DeviceManager

DEVICES = DeviceManager()

__all__ = ["PressureGauge", 
           "Shutter", 
           "Source",
           "Motor",
           "SubstrateMotor", 
           "Camera",
           "LoadingMotor",
           "DEVICES"
           ]