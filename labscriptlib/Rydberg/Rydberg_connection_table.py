from labscript import start, stop, ClockLine, DigitalOut
from labscript_devices.NI_DAQmx.models.NI_PCI_6733 import NI_PCI_6733
from labscript_devices.NI_DAQmx.models.NI_PCIe_6738 import NI_PCIe_6738
#from labscript_devices.NI_DAQmx.models.NI_PCI_6534 import NI_PCI_6534
from labscript_devices.PulseBlasterUSB import PulseBlasterUSB
from user_devices.Rydberg.PTSControl.labscript_devices import PTSControl
from user_devices.Rydberg.BaslerCamera.labscript_devices import BaslerCamera
from user_devices.Rydberg.AD9959ArduinoComm.labscript_devices import AD9959ArduinoComm, AD9959ArduinoTriggerDigital, AD9959ArduinoTriggerAnalog
from user_devices.Rydberg.Agilent33250a.labscript_devices import Agilent33250a
from user_devices.Rydberg.NICounter.labscript_devices import NICounter


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

    PulseBlasterUSB(
        name='pulseblaster_0',
        board_number=1,
    )

    ###
    ### Clocks for NI cards and initialize NI cards
    ### 

    ClockLine(
        name='ni_6733_clk',
        pseudoclock=pulseblaster_0.pseudoclock,
        connection='flag 1',
    )

    NI_PCI_6733(
        name="ni_6733A", 
        parent_device=ni_6733_clk, 
        clock_terminal = "/AO_A/PFI0", 
        MAX_name = "AO_A"
        )

    #####

    # ClockLine(
    #     name='ni_6733B_clk',
    #     pseudoclock=pulseblaster_0.pseudoclock,
    #     connection='flag 1',
    # )

    NI_PCI_6733(
        name="ni_6733B", 
        parent_device=ni_6733_clk, 
        clock_terminal = "/AO_B/PFI0", 
        MAX_name = "AO_B"
        )

    #####

    # ClockLine(
    #     name='ni_6733C_clk',
    #     pseudoclock=pulseblaster_0.pseudoclock,
    #     connection='flag 1',
    # )

    NI_PCI_6733(
        name="ni_6733C", 
        parent_device=ni_6733_clk, 
        clock_terminal = "/AO_C/PFI0", 
        MAX_name = "AO_C"
    )

    #####

    ClockLine(
        name='ni_6738_clk',
        pseudoclock=pulseblaster_0.pseudoclock,
        connection='flag 1',
    )

    NI_PCIe_6738(
        name="ni_6738", 
        parent_device=ni_6738_clk, 
        clock_terminal = "/AO_32/PFI0", 
        MAX_name = "AO_32"
    )

    ######
    ###### Devices
    ######

    # MOT and Repump beatnote locking
    AD9959ArduinoTriggerDigital(
        name="motl_trigger",
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 9",
        default_value=0,
    )

    AD9959ArduinoTriggerDigital(
        name="repump_trigger",
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 11",
        default_value=0,
    )

    AD9959ArduinoComm(
        name="motl_repump_ad9959",
        parent_device=None,
        com_port="COM3",
        baud_rate = 115200,
        channel_mappings={"MOT":'ch0', "Repump":'ch3'},
        div_32=True
    )

    Trigger(
        name='spcm_counter_trigger',
        parent_device=pulseblaster_0.direct_outputs,
        connection='flag 7',
        default_value=0,
    )

    NICounter(
        name='spcm_counter', 
        parent_device=spcm_counter_trigger,
        MAX_name='Dev6', 
        counter_channel="Dev6/Ctr0", 
        input_channel="/Dev6/PFI39", 
        gate_channel="/Dev6/PFI38", 
    )

    Trigger(
        name='pts_rydberg_trigger',
        parent_device=pulseblaster_0.direct_outputs,
        connection='flag 0'
    )

    PTSControl(
        name='pts_rydberg',
        parent_device=pts_rydberg_trigger,
        device_serial=b'10440000K8',
    )

    Trigger(
        name='pts_probe_trigger',
        parent_device=pulseblaster_0.direct_outputs,
        connection='flag 3'
    )

    PTSControl(
        name='pts_probe',
        parent_device=pts_probe_trigger,
        device_serial=b'10440000KE',
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
        limits=(0, 5)
    )

    
    AnalogOut(
        name="small_z_coil",
        parent_device=ni_6733C,
        connection="ao3",
        default_value=0,
        limits=(0, 5)
    )

    AnalogOut(
        name="small_y_coil",
        parent_device=ni_6733C,
        connection="ao2",
        default_value=0,
        limits=(0, 5)
    )

    AnalogOut(
        name="small_x_coil",
        parent_device=ni_6733C,
        connection="ao3",
        default_value=0,
    )

    AnalogOut(
        name="gradient_coil",
        parent_device=ni_6733C,
        connection="ao4",
        default_value=0,
        limits=(0, 3.5)
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
        limits=(0, 3)
    )

    DigitalOut(
        name='motl_aom_switch',
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 20",
        default_value=0,
    )   

    AnalogOut(
        name="repump_aom_power",
        parent_device=ni_6733B,
        connection="ao5",
        default_value=0,
        limits=(0, 3)
    )


    DigitalOut(
        name='repump_aom_switch',
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 19",
        default_value=0,
    )   

    AnalogOut(
        name="imaging_aom_power",
        parent_device=ni_6733B,
        connection="ao3",
        default_value=0,
        limits=(0, 3)
    )

    DigitalOut(
        name='imaging_aom_switch',
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 13",
        default_value=0,
    )   

    AnalogOut(
        name="dt852_aom_power",
        parent_device=ni_6733C,
        connection="ao7",
        default_value=0,
        limits=(0, 3)
    )

    DigitalOut(
        name='dt852_aom_switch',
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 16",
        default_value=0,
    )   

    AnalogOut(
        name="dt1064_aom_power",
        parent_device=ni_6733B,
        connection="ao2",
        default_value=0,
        limits=(0, 3)
    )

    DigitalOut(
        name='dt1064_aom_switch',
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 15",
        default_value=0,
    )   

    AnalogOut(
        name="probe_aom_power",
        parent_device=ni_6733A,
        connection="ao2",
        default_value=0,
        limits=(0, 3)
    )

    DigitalOut(
        name='probe_aom_switch',
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 18",
        default_value=0,
    )   

    ### Dummy Devices: Analog cards need an even number of ouputs to not through errors
    AnalogOut(
        name="dummy_6733A",
        parent_device=ni_6733A,
        connection="ao7",
        default_value=0,
    )
    
    # AnalogOut(
    #     name="dummy_6738",
    #     parent_device=ni_6738,
    #     connection="ao31",
    #     default_value=0,
    # )

    ## Camera

    BaslerCamera(
        'basler',
        parent_device=pulseblaster_0.direct_outputs,
        # I made a custom class from PylonCamera that initializes the camera by searching a list rather than using a serial number,
        # because I couldn't get the SN to work. This approach will break if we ever have more than one basler camera connected at a time
        # This serial number is irrelevant and is not used in camera creation
        serial_number=-1,
        connection='flag 5',
        trigger_duration=50e-6,
        camera_attributes= {
            'ExposureAuto': 'Off',
            'GainAuto': 'Off',
            'Gain': 0.0,
            'BlackLevel': 0.0,
            'Gamma': 1.0,
            'ExposureMode': 'Timed',
            'ExposureTime': 50.0,
            'TriggerMode': 'On', # Can set to 'Off' for software triggering, 'On' for external triggering
            'LineSelector': 'Line1',
            'CounterEventSource': 'FrameStart',
            'CounterResetActivation': 'RisingEdge',
            'TriggerActivation': "RisingEdge",
            'TriggerDelay': 0,
            "PixelFormat": "Mono8"
        }
    )

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