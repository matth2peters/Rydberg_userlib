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



from blacs.tab_base_classes import Worker


class PrototypeDeviceWorker(Worker):

    def init (self):
        # Once off device initialisation code called when the
        # worker process is first started.
        # Usually this is used to create the connection to the
        # device and/or instantiate the API from the device
        # manufacturer

        # here you may start up a serial connection, define variables, etc.

        my_device_name = self.name

    def do_work(self, arg1, arg2):
        # this function gets called by the button or by transition_to_buffered
        # You should be able to see the output in the workers blacs tab in the gui!
        print(arg1)
        print(arg2)

        self.success = "Success"
        return self.success

    def shutdown ( self ):
        # Once off device shutdown code called when the
        # BLACS exits
        self.connection.close()

    def program_manual (self, front_panel_values):
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

        # From the H5 sequence file, get the sequence we want programmed into the device
        with h5py.File(h5_file_path, 'r') as hdf5_file:
            
            devices = hdf5_file['devices'][device_name]

            command_list = devices['command_list']
            # decode into python-readable strings
            command_list = [n.decode('utf-8') for n in command_list]

            self.do_work(command_list[0], command_list[1])
            self.h5_file_path = h5_file_path
        final_values = {}
        return final_values


    def transition_to_manual (self):
        # Called when the shot has finished , the device should
        # be placed back into manual mode
        # return True on success

        # here data can be saved by doing the reverse of reading the h5 file in transition_to_buffer
        with h5py.File(self.h5_file_path, 'a') as hdf5_file:
            data_group = hdf5_file['data']
            data_group.require_group('traces')
            dset = data_group.require_dataset('Succuess?', (1,), dtype='S30')
            dset[0] = self.success.encode("ascii", "ignore")
             
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

