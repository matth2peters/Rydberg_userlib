#####################################################################
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from collections import defaultdict
import time

import labscript_utils.h5_lock  # Must be imported before importing h5py.
import h5py
from matplotlib.pyplot import pause
import numpy as np
from labscript.labscript import set_passed_properties
import time
from pathlib import Path
from labscript import MHz

from blacs.tab_base_classes import Worker


class PTSControlWorker(Worker):

    def init (self):
        # Once off device initialisation code called when the
        # worker process is first started .
        # Usually this is used to create the connection to the
        # device and/or instantiate the API from the device
        # manufacturer

        global ctypes; import ctypes
        # This is the path to the folder containing the folder containing bit files for the FPGA
        self.script_path = Path(r'C:\Users\RoyDAQ\labscript-suite\Rydberg_userlib\user_devices\Rydberg\PTSControl\FPGA_Bit_files')
        # the Opal Kelly library that communicates with the FPGA
        self.oklib = ctypes.WinDLL(str(Path.joinpath(self.script_path, "okFrontPanel.dll")))
        print("Connecting to FPGA {}".format(self.device_name))
        self.FPGA = self.oklib.okFrontPanel_Construct()

        # Count the # of devices the program has detected (to see if it's working)
        number_devices = self.oklib.okFrontPanel_GetDeviceCount(self.FPGA)

        buf = ctypes.create_string_buffer(128)

        serials_in = []
        
        for i in range(number_devices):
            self.oklib.okFrontPanel_GetDeviceListSerial(self.FPGA,i,buf)
            serials_in.append(buf.value)
        
        print("Found {} devices with serials {}".format(number_devices, repr(serials_in)))
        

        # Try to connect
        self._check(self.oklib.okFrontPanel_OpenBySerial(self.FPGA, self.device_serial))

        print("Successful Connect to device {}".format(self.device_serial))


    def set_frequency(self, set_frequency_MHz, freq_step_size=1):
        """set the frequency of the PTS. This code is taken from aditya and seems to be doing a frequency sweep. I commented out the frequency sweep parts and 
        only left the part that sets the final frequency

        Args:
            set_frequency ([int]): frequency in MHz
            freq_step_size ([int]): the steps between frequencies in MHz
        """
        
        current_frequency_MHz = self.get_frequency()

        # sign = np.sign(set_frequency_MHz - current_frequency_MHz)
        # t0 = time.time()
        # # step to the set frequency in increments of freq_step_size
        # while np.abs(set_frequency_MHz  - current_frequency_MHz)  >  freq_step_size_MHz:
        #     current_frequency_MHz = currentFreqMHz + sign * freq_step_size_MHz
        #     self.set_freq_help(current_frequency_MHz)
        
        self.set_freq_help(set_frequency_MHz)
        
        # t1 = time.time()
        # print("Total sweep time {:.3f} ms".format((t1-t0)/1e3))


    def set_freq_help(self, freq_MHz):
        """ The FPGA takes in a gross BCD format. This function helps is responsible for sending the actual commands to the FPGA in the format it wants
        I have no idea how it works. Ask Aditya.
        """
        
        # convert to insane transmission format 
        freq_100_Hz = int(round(freq_MHz*10000))
        
        freq_100_Hz_string = format(freq_100_Hz, 'd')
        
        freq_LSB = int(freq_100_Hz_string[-4:], 16)
        freq_MSB = int(freq_100_Hz_string[:-4], 16)
        

        # this is from WireInParamsSlowScanONLYfreq.vi
        #0x04 -> freqLSB, 0x05 -> freqMSB, 0xFFFF is a mask.. can't find it in the API documentation, but is there in the LabView program

        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x05), ctypes.c_uint16(freq_MSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x04), ctypes.c_uint16(freq_LSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_UpdateWireIns(self.FPGA)
        

        # 0x11 -> goToFreq
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x11), ctypes.c_uint16(1), ctypes.c_uint16(1))
        self.oklib.okFrontPanel_UpdateWireIns(self.FPGA)
        
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x11), ctypes.c_uint16(0), ctypes.c_uint16(1))
        self.oklib.okFrontPanel_UpdateWireIns(self.FPGA)

    def setup_fast_scan(self, min_freq, max_freq, step, num_cycles_between_ramp_steps=1e2, ramp_step=0.8/8):
        """Same as above; it's not entirely clear to me what the code is doing in detail. Broadly, this sets up the FPGA for incrementing the output frequency by the amount "step"
            It seems only the "step" functionality is used and not the "ramp".
            ie you need to trigger it each time you want it to move to the next value. The ramp pin is not used

        Args:
            min_freq ([float]): starting frequency in MHz
            max_freq (float): ending frequency in MHz
            step ([float]): how much to step the frequency in MHz
            num_cycles_between_ramp_steps ([int], optional): This is not used since we do not use the ramp pin, but if we did, it would control the rate at which the ramp moves to the next value. Defaults to 1e2.
            ramp_step ([float]): Same as the previous parameter: this controls the step size of the ramp in MHz
        """
        
        min_freq_100Hz = int(round(min_freq['MHz']*10000))
        min_freq_100HzStr = format(min_freq_100Hz,'d')
        min_freqLSB = int(min_freq_100HzStr[-4:],16)
        min_freqMSB = min_freq_100HzStr[:-4]
        if min_freqMSB == '':
            min_freqMSB = 0
        else:
            min_freqMSB = int(min_freqMSB, 16)
        
        max_freq_100Hz = int(round(max_freq['MHz']*10000))
        max_freq_100HzStr = format(max_freq_100Hz,'d')
        max_freqLSB = int(max_freq_100HzStr[-4:],16)
        max_freqMSB = max_freq_100HzStr[:-4]
        if max_freqMSB == '':
            max_freqMSB = 0
        else:
            max_freqMSB = int(max_freqMSB, 16)
        
        step_100Hz = int(round(step['MHz']*10000))
        step_100HzStr = format(step_100Hz,'d')
        stepLSB = int(('1111'+step_100HzStr[-4:])[-4:], 16)
        stepMSB = int(('1111'+ step_100HzStr[:-4])[-4:], 16)
        
        ramp_step_100Hz = int(round(ramp_step*10000))
        ramp_step_100HzStr = format(ramp_step_100Hz,'d')
        ramp_stepLSB = int(('1111'+ ramp_step_100HzStr[-4:])[-4:], 16)
        ramp_stepMSB = int(('1111'+ ramp_step_100HzStr[:-4])[-4:], 16)
                
        num_cycles_between_ramp_steps_str = format(int(num_cycles_between_ramp_steps),'d')
        num_cycles_between_ramp_steps_LSB = int(num_cycles_between_ramp_steps_str[-4:],16)
        num_cycles_between_ramp_steps_MSB = num_cycles_between_ramp_steps_str[:-4]
        if num_cycles_between_ramp_steps_MSB == '':
            num_cycles_between_ramp_steps_MSB = 0
        else:
            num_cycles_between_ramp_steps_MSB = int(num_cycles_between_ramp_steps_MSB,16)            
    
        # 0xFFFF is a mask
        # 0x00 -> min freq LSB, 0x01 -> min freq MSB
        # 0x04 -> max freq LSB, 0x05 -> max freq MSB
        # 0x02 -> step up freq LSB, 0x03 -> step up freq MSB
        # 0x06 -> ramp dn freq LSB, 0x07 -> ramp dn freq MSB
        # 0x09 -> num_cycles_between_ramp_steps_LSB, 0x010 -> num_cycles_between_ramp_steps_MSB

        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x00), ctypes.c_uint16(min_freqLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x01), ctypes.c_uint16(min_freqMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x04), ctypes.c_uint16(max_freqLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x05), ctypes.c_uint16(max_freqMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x02), ctypes.c_uint16(stepLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x03), ctypes.c_uint16(stepMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x06), ctypes.c_uint16(ramp_stepLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x07), ctypes.c_uint16(ramp_stepMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x09), ctypes.c_uint16(num_cycles_between_ramp_steps_LSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.FPGA, ctypes.c_uint8(0x10), ctypes.c_uint16(num_cycles_between_ramp_steps_MSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_UpdateWireIns(self.FPGA)
    

    def upload_bit_file(self, local_path):
        """Upload the bit file to the FPGA. See "Optical Imaging of Rydberg Atoms" by Anton Mazurenko for a description of the different files

        Args:
            local_path ([str]): The path to the bit file inside the folder
        """

        # encode the file path such that it matches c++ types, otherwise the OK library won't recognize the path
        bit_path = str(Path.joinpath(self.script_path, local_path)).encode("utf-8")
        print("Uploading {} to FPGA".format(bit_path))
        self._check(self.oklib.okFrontPanel_LoadDefaultPLLConfiguration(self.FPGA))
        return self._check(self.oklib.okFrontPanel_ConfigureFPGA(self.FPGA, bit_path))

    def get_frequency(self):
        """
        Get the frequency of the device
        """

        self.oklib.okFrontPanel_UpdateWireOuts(self.FPGA)
        self.oklib.okFrontPanel_GetWireOutValue.restype = ctypes.c_uint32
        val20 = self.oklib.okFrontPanel_GetWireOutValue(self.FPGA,ctypes.c_int32(0x20))
        val21 = self.oklib.okFrontPanel_GetWireOutValue(self.FPGA,ctypes.c_int32(0x21))

        # these numbers should are converted into hex strings and then interpreted
        # as base-10 strings.
        
        # So, a frequency of 1234.5678 MHz becomes 12345678 * 100 Hz
        # converted into string '12345678'
        # then split into two strings '1234', '5678'
        # then these strings are interpreted as hex numbers 0x1234, 0x5678
        # and these two hex numbers are sent to the card.
        # To retrieve the frequency here, we do this in reverse.
        
        # make hex string
        lower_hex = format(val20,'x')
        upper_hex = format(val21,'x')
        
        # re-interpret as decimal string. This could give error if abcdef appears in string...
        lower_int = int(lower_hex,10)
        upper_int = int(upper_hex,10)
        
        freq_MHz = lower_int*0.0001 + upper_int
        
        return freq_MHz
        

    def shutdown (self):
        # Once off device shutdown code called when the
        # BLACS exits
        self.oklib.okFrontPanel_Destruct(self.FPGA)

    def program_manual ( self , front_panel_values ):
        # Update the output state of each channel using the values
        # in front_panel_values ( which takes the form of a
        # dictionary keyed by the channel names specified in the
        # BLACS GUI configuration
        # return a dictionary of coerced / quantised values for each
        # channel , keyed by the channel name (or an empty dictionary )
        return {}
    def transition_to_buffered ( self , device_name , h5_file_path,
    initial_values , fresh ):
        # Access the HDF5 file specified and program the table of
        # hardware instructions for this device .
        # Place the device in a state ready to receive a hardware
        # trigger (or software trigger for the master pseudoclock )
        #
        # The current front panel state is also passed in as
        # initial_values so that the device can ensure output
        # continuity up to the trigger .
        #
        # The fresh keyword indicates whether the entire table of
        # instructions should be reprogrammed (if the device supports
        # smart programming )
        # Return a dictionary , keyed by the channel names , of the
        # final output state of the shot file . This ensures BLACS can
        # maintain output continuity when we return to manual mode
        # after the shot completes .

        self.h5_filepath = h5_file_path
        self.device_name = device_name

        # From the H5 sequence file, get the sequence we want programmed into AWG and command it
        with h5py.File(h5_file_path, 'r') as hdf5_file:
            
            devices = hdf5_file['devices'][device_name]

            dset_freqs = devices['min_max_step_freq']
            min_freq, max_freq, step_freq = dset_freqs[:]

            mode = devices['mode'][0].decode('utf-8')
            print(mode)

            if "Slow" in mode or "Fast" in mode:

                self.upload_bit_file(mode)
                if mode == "Slow Control":
                    self.set_frequency(min_freq)

                if "Fast" in mode:
                    self.setup_fast_scan(min_freq, max_freq, step_freq)



        final_values = {}
        return final_values


    def transition_to_manual ( self ):
        # Called when the shot has finished , the device should
        # be placed back into manual mode
        # return True on success
        self.upload_bit_file("slowcontrol.bit")
        
        return True

    def abort_transition_to_buffered ( self ):
        # Called only if transition_to_buffered succeeded and the
        # shot if aborted prior to the initial trigger
        # return True on success
        return True
    def abort_buffered ( self ):
        # Called if the shot is to be abort in the middle of
        # the execution of the shot ( after the initial trigger )
        # return True on success
        return True

    def _check(self, err):
        if err >= 0:
            return err
        else:
            error_string = ''
            if err == -1:
                error_string = 'Failed'
            elif err == -2:
                error_string = 'Timeout'
            elif err == -3:
                error_string = 'DoneNotHigh'
            elif err == -4:
                error_string = 'TransferError'
            elif err == -5:
                error_string = 'CommunicationError'
            elif err == -6:
                error_string = 'InvalidBitstream'
            elif err == -7:
                error_string = 'FileError'
            elif err == -8:
                error_string = 'DeviceNotOpen'
            elif err == -9:
                error_string = 'InvalidEndpoint'
            elif err == -10:
                error_string = 'InvalidBlockSize'
            elif err == -11:
                error_string = 'I2CRestrictedAddress'
            elif err == -12:
                error_string = 'I2CBitError'
            elif err == -13:
                error_string = 'I2CNack'
            elif err == -14:
                error_string = 'I2CUnknownStatus'
            elif err == -15:
                error_string = 'UnsupportedFeature'
            elif err == -16:
                error_string = 'FIFOUnderflow'
            elif err == -17:
                error_string = 'FIFOOverflow'
            elif err == -18:
                error_string = 'DataAlignmentError'
                
            raise RuntimeError('Opal Kelly failed with error: {}'.format(error_string))