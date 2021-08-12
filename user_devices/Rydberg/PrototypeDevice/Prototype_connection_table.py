from labscript_devices.DummyPseudoclock.labscript_devices import DummyPseudoclock
from user_devices.Rydberg.PrototypeDevice.labscript_devices import PrototypeDevice


from labscript import (
    ClockLine,
    AnalogOut,
    DigitalOut,
    MHz,
    Trigger,
    start,
    stop
)

def cxn_table():

    DummyPseudoclock()
    
    PrototypeDevice(
        name='ProtoDev',
        parent_device=dummy_pseudoclock.clockline
    )


if __name__ == '__main__':

    cxn_table()
    start()
    stop(1)