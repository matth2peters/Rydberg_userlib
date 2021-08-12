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
import numpy as np
from labscript.labscript import set_passed_properties


from blacs.tab_base_classes import Worker


class AD9959ArduinoCommWorker(Worker):

    def init (self):
        # Once off device initialisation code called when the
        # worker process is first started .
        # Usually this is used to create the connection to the
        # device and/or instantiate the API from the device
        # manufacturer

        global serial; import serial

        # mappings between commands sent to arduino and their meaning
        self.command_dict = {"freq":1, "phase":2}
        
        # start up the serial connection
        self.connection = serial.Serial(self.com_port, baudrate=self.baud_rate, timeout=0.1)


    
    def set_frequency(self, channel, freq_list):
        """Command the arduino to set the frequency of the specified DDS channel

        Args:
            channel (int): The channel to set
            freq_list ([int list]): The list of frequencies to set in MHz
            
        """
        # div_32 bool: for the MOT and Repump locks, the AD4007 divides the actual frequency by 32
        if self.div_32:
            freq_list = [n / 32.0 for n in freq_list]
        # number of frequencies to write
        self.connection.write(channel.to_bytes(1, 'big'))
        self.connection.write(self.command_dict['freq'].to_bytes(1, 'big'))
        self.connection.write(len(freq_list).to_bytes(1, 'big'))

        # convert each frequency into a byte array 4 bytes long, then send each 
        # sequentially. 
        for freq in freq_list:
            freq = int(freq * 1e6) # convert from MHz to Hz which is what arduino reads
            byte_array = freq.to_bytes(4, 'big')
            for by in byte_array:
                self.connection.write(by.to_bytes(1, 'big'))

    def set_phase(self, channel, phase):
        """Command the arduino to set the phase of the specified DDS channel

        Args:
            channel (int): The channel to set
            freq_list ([int list]): The list of frequencies to set in MHz
        """

        # The Phase register is 14 bits long in the DDS, so convert a degree into bits to send to arduino
        phase_int = int(phase / 360.0 * 2**14)
        num_phases = 1
        # number of frequencies to write
        self.connection.write(channel.to_bytes(1, 'big'))
        self.connection.write(self.command_dict['phase'].to_bytes(1, 'big'))
        self.connection.write(num_phases.to_bytes(1, 'big'))

        # convert each into a byte array 2 bytes long, then send each 
        # sequentially.
        byte_array = phase_int.to_bytes(2, 'big')
        for by in byte_array:
            self.connection.write(by.to_bytes(1, 'big'))

    def shutdown ( self ):
        # Once off device shutdown code called when the
        # BLACS exits
        self.connection.close()

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

        # self.h5_filepath = h5_file
        # self.device_name = device_name

        # From the H5 sequence file, get the sequence we want programmed into the arduino
        with h5py.File(h5_file_path, 'r') as hdf5_file:
            
            devices = hdf5_file['devices'][device_name]

            for channel in devices.keys():
                print("Setting Frequency for {}".format(channel))

                if "frequency" in channel:
                    # extract the integer part of the name
                    channel_int = int(channel[-1])
                    freq_list = list(devices[channel])
                    print(list(freq_list))
                    # program it into the arduino
                    self.set_frequency(channel_int, freq_list)

                if "phase" in channel:
                    print("Setting Phase for {}".format(channel))
                    channel_int = int(channel[-1])
                    # unpack the list
                    phase = devices[channel][0]
                    print("Phase {} deg".format(phase))
                    self.set_phase(channel_int, phase)

                # give the arduino time to implement the changes
                time.sleep(1e-4)

        final_values = {}
        return final_values


    def transition_to_manual ( self ):
        # Called when the shot has finished , the device should
        # be placed back into manual mode
        # return True on success
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

