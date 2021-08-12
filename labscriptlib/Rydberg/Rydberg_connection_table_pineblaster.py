from labscript import start, stop, ClockLine, DigitalOut
from labscript_devices.NI_DAQmx.models.NI_PCI_6733 import NI_PCI_6733
from labscript_devices.NI_DAQmx.models.NI_PCIe_6738 import NI_PCIe_6738
from labscript_devices.NI_DAQmx.models.NI_PCI_6534 import NI_PCI_6534
from labscript_devices.NI_DAQmx.models.NI_PCI_6602 import NI_PCI_6602
from labscript_devices.PulseBlasterESRPro200 import PulseBlasterESRPro200
from labscript_devices.PineBlaster import PineBlaster
#from labscript_devices.PulseBlasterESRPro500 import PulseBlasterESRPro500
from user_devices.Rydberg.PTSControl.labscript_devices import PTSControl
from user_devices.Rydberg.BaslerCamera.labscript_devices import BaslerCamera
from user_devices.Rydberg.AD9959ArduinoComm.labscript_devices import AD9959ArduinoComm, AD9959ArduinoTriggerDigital, AD9959ArduinoTriggerAnalog


from labscript import (
    ClockLine,
    AnalogOut,
    AnalogIn,
    DigitalOut,
    MHz,
    Trigger,
    start,
    stop
)

def cxn_table():

    PineBlaster(
        name="pineblaster_0",
        trigger_connection="port0/line15",
        usbport="COM4",
    )


    ###
    ### NI CARDS
    ### 

    NI_PCI_6602(
        name='ni_6602',
        parent_device=pineblaster_0.clockline,
        clock_terminal='/Dev6/PFI32',
        MAX_name='Dev6'
    )


    ###

    NI_PCI_6534(
        name='ni_6534',
        parent_device=pineblaster_0.clockline,
        clock_terminal='/Dev5/PFI2',
        MAX_name='Dev5'
    )

    ###

    NI_PCI_6733(
        name="ni_6733A", 
        parent_device=pineblaster_0.clockline, 
        clock_terminal = "/AO_A/PFI0", 
        MAX_name = "AO_A"
        )

    #####


    NI_PCI_6733(
        name="ni_6733B", 
        parent_device=pineblaster_0.clockline, 
        clock_terminal = "/AO_B/PFI0", 
        MAX_name = "AO_B"
        )

    #####


    NI_PCI_6733(
        name="ni_6733C", 
        parent_device=pineblaster_0.clockline, 
        clock_terminal = "/AO_C/PFI0", 
        MAX_name = "AO_C"
    )

    #####


    NI_PCIe_6738(
        name="ni_6738", 
        parent_device=pineblaster_0.clockline, 
        clock_terminal = "/AO_32/PFI0", 
        MAX_name = "AO_32"
    )

    ######
    ###### Devices
    ######

    # MOT and Repump beatnote locking
    AD9959ArduinoTriggerAnalog(
        name="motl_trigger",
        parent_device=ni_6738,
        connection="ao0",
        default_value=0,
        limits=(0, 3.3)
    )

    AD9959ArduinoTriggerAnalog(
        name="repump_trigger",
        parent_device=ni_6738,
        connection="ao1",
        default_value=0,
        limits=(0, 3.3)
    )

    AD9959ArduinoComm(
        name = "motl_repump_arduino",
        parent_device=None,
        com_port = 3,
        baud_rate = 115200,
    )

    ### COILS

    # AnalogOut(
    #     name="big_z_coil",
    #     parent_device=ni_6738,
    #     connection="ao4",
    #     default_value=0,
    # )

    AnalogOut(
        name="big_x_coil",
        parent_device=ni_6733C,
        connection="ao1",
        default_value=0,
    )

    
    AnalogOut(
        name="small_z_coil",
        parent_device=ni_6733C,
        connection="ao3",
        default_value=0,
    )

    AnalogOut(
        name="small_y_coil",
        parent_device=ni_6733C,
        connection="ao2",
        default_value=0,
    )

    # AnalogOut(
    #     name="small_x_coil",
    #     parent_device=ni_6733C,
    #     connection="ao3",
    #     default_value=0,
    # )

    AnalogOut(
        name="gradient_coil",
        parent_device=ni_6733C,
        connection="ao4",
        default_value=0,
    )

    # switch to ditgital once tested
    AnalogOut(
        name='gradient_coil_switch',
        parent_device=ni_6733C,
        connection="ao0",
        default_value=0,
    )   

    ### LASERS
    AnalogOut(
        name="motl_aom_power",
        parent_device=ni_6733B,
        connection="ao6",
        default_value=0,
    )

    AnalogOut(
        name='motl_aom_switch',
        parent_device=ni_6738,
        connection="ao2",
        default_value=0,
        limits=(0, 3.3)
    )   

    AnalogOut(
        name="repump_aom_power",
        parent_device=ni_6733B,
        connection="ao5",
        default_value=0,
    )


    AnalogOut(
        name='repump_aom_switch',
        parent_device=ni_6738,
        connection="ao3",
        default_value=0,
        limits=(0, 3.3)
    )   

    AnalogOut(
        name="imaging_aom_power",
        parent_device=ni_6733B,
        connection="ao3",
        default_value=0,
    )

    AnalogOut(
        name='imaging_aom_switch',
        parent_device=ni_6738,
        connection="ao4",
        default_value=0,
        limits=(0, 3.3)
    )   

    AnalogOut(
        name="dt852_aom_power",
        parent_device=ni_6733C,
        connection="ao7",
        default_value=0,
    )

    AnalogOut(
        name='dt852_aom_switch',
        parent_device=ni_6738,
        connection="ao5",
        default_value=0,
    )   

    AnalogOut(
        name="dt1064_aom_power",
        parent_device=ni_6733B,
        connection="ao2",
        default_value=0,
    )

    AnalogOut(
        name='dt1064_aom_switch',
        parent_device=ni_6738,
        connection="ao6",
        default_value=0,
        limits=(0, 3.3)
    )   

    AnalogOut(
        name="probe_aom_power",
        parent_device=ni_6733A,
        connection="ao2",
        default_value=0,
    )

    AnalogOut(
        name='probe_aom_switch',
        parent_device=ni_6738,
        connection="ao7",
        default_value=0,
        limits=(0, 3.3)
    )   

    #     Trigger(
    #     name='PTScontrol_trigger',
    #     parent_device=pulseblaster_0.direct_outputs,
    #     connection='flag 3'
    # )

    PTSControl(
        name='PTScontrol',
        #trigger=PTScontrol_trigger,
        device_serial=b'10440000KE',
    )

    ### Dummy Devices: Analog cards need an even number of ouputs to not through errors
    AnalogOut(
        name="dummy0",
        parent_device=ni_6733A,
        connection="ao7",
        default_value=0,
    )

    # AnalogOut(
    #     name="dummy1",
    #     parent_device=ni_6534,
    #     connection="port0/line5",
    #     default_value=0,
    # )

    # DigitalOut(
    #     name="ddummy1",
    #     parent_device=ni_6534,
    #     connection="port1/line0",
    #     default_value=0,
    # )

    ### Counter


    # AnalogOut(
    #     name="dummy1",
    #     parent_device=ni_6733C,
    #     connection="ao7",
    #     default_value=0,
    # )

    ## Camera

    # BaslerCamera(
    #     'basler',
    #     parent_device=ni_6534,
    #     # I made a custom class from PylonCamera that initializes the camera by searching a list rather than using a serial number,
    #     # because I couldn't get the SN to work. This approach will break if we ever have more than one basler camera connected at a time
    #     # This serial number is irrelevant and is not used in camera creation
    #     serial_number=-1,
    #     connection='port0/line4',
    #     trigger_duration=1e-6,
    #     camera_attributes= {
    #         'ExposureAuto': 'Off',
    #         'GainAuto': 'Off',
    #         'Gain': 0.0,
    #         'BlackLevel': 0.0,
    #         'Gamma': 1.0,
    #         'ExposureMode': 'Timed',
    #         'ExposureTime': 50.0,
    #         'TriggerMode': 'Off',#'On', # Can set to 'Off' for software triggering, 'On' for external triggering
    #         'LineSelector': 'Line1',
    #         'CounterEventSource': 'FrameStart',
    #         'CounterResetActivation': 'RisingEdge',
    #         'TriggerActivation': "RisingEdge",
    #         'TriggerDelay': 0,
    #         "PixelFormat": "Mono8"
    #     }
    # )

    # IMAQdxCamera(
    # 'firebrain701b',
    # parent_device=pulseblaster_0.direct_outputs,
    # connection='flag 5',
    # serial_number=0x814436300001000,
    # trigger_duration=1e-7,
    # minimum_recovery_time=1e-2,
    # camera_attributes = {
    #     'AcquisitionAttributes::Bayer::Algorithm': 'Bilinear',
    #     'AcquisitionAttributes::Bayer::GainB': 1.0,
    #     'AcquisitionAttributes::Bayer::GainG': 1.0,
    #     'AcquisitionAttributes::Bayer::GainR': 1.0,
    #     'AcquisitionAttributes::Bayer::Pattern': 'Use hardware value',
    #     'AcquisitionAttributes::BitsPerPixel': 'Use hardware value',
    #     'AcquisitionAttributes::Controller::DesiredStreamChannel': 0,
    #     'AcquisitionAttributes::Controller::StreamChannelMode': 'Automatic',
    #     'AcquisitionAttributes::Height': 1024,
    #     'AcquisitionAttributes::ImageDecoderCopyMode': 'Auto',
    #     'AcquisitionAttributes::OffsetX': 0,
    #     'AcquisitionAttributes::OffsetY': 0,
    #     'AcquisitionAttributes::OutputImageType': 'Auto',
    #     'AcquisitionAttributes::OverwriteMode': 'Get Newest',
    #     'AcquisitionAttributes::PacketSize': 3072,
    #     'AcquisitionAttributes::PixelFormat': 'Mono 8',
    #     'AcquisitionAttributes::ReceiveTimestampMode': 'None',
    #     'AcquisitionAttributes::ReserveDualPackets': 0,
    #     'AcquisitionAttributes::ShiftPixelBits': 0,
    #     'AcquisitionAttributes::Speed': '400 Mbps',
    #     'AcquisitionAttributes::SwapPixelBytes': 0,
    #     'AcquisitionAttributes::Timeout': 5000,
    #     'AcquisitionAttributes::VideoMode': 'Format 7, Mode 0, 1280 x 1024',
    #     'AcquisitionAttributes::Width': 1280,
    #     'CameraAttributes::AutoExposure::Mode': 'Ignored',
    #     'CameraAttributes::Brightness::Mode': 'Relative',
    #     'CameraAttributes::Brightness::Value': 418.0,
    #     'CameraAttributes::Gain::Mode': 'Relative',
    #     'CameraAttributes::Gain::Value': 0.0,
    #     'CameraAttributes::Gamma::Mode': 'Relative',
    #     'CameraAttributes::Gamma::Value': 10.0,
    #     'CameraAttributes::Sharpness::Mode': 'Relative',
    #     'CameraAttributes::Sharpness::Value': 414.0,
    #     'CameraAttributes::Shutter::Mode': 'Relative',
    #     'CameraAttributes::Shutter::Value': 200.0,
    #     'CameraAttributes::Trigger::TriggerActivation': 'Level High',
    #     'CameraAttributes::Trigger::TriggerMode': 'Mode 0',
    #     }
    # )


if __name__ == '__main__':

    cxn_table()
    start()
    stop(1)