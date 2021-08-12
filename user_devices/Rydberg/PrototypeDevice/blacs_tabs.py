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



from blacs.device_base_class import DeviceTab, define_state
from qtutils.qt.QtCore import*
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from PyQt5.QtWidgets import QGridLayout, QLabel

class PrototypeDeviceTab(DeviceTab):
    def initialise_GUI ( self ):
        """Initializes the GUI tab for the arduino/dds communication
        """
        
        # pull the layout of the tab so that we can place widgets in it
        layout = self.get_tab_layout()

        # Get properties from connection table.
        device = self.settings['connection_table'].find_by_name(
            self.device_name
        )
        
        # An example property
        self.name = device.properties['name']

        # create a grid layout row that we can add to the layout
        # inside the grid, spots are indexed by (row, column)
        gui_row = QGridLayout()

        # add the name of the device to the grid at the (0, 0) spot
        device_name_label = QLabel()
        device_name_label.setText(self.name)
        gui_row.addWidget(device_name_label, 0, 0)

        # add a device with some functionality at the (0, 1) spot
        device_button = QPushButton()
        device_button.setText("Push Me!")
        device_button.setStyleSheet("border :1px solid black")
        device_button.clicked.connect(self.on_click)
        gui_row.addWidget(device_button, 0, 1)

        # finally, add the row to the blacs GUI
        layout.addLayout(gui_row)



    # These guys tell you that this function will only do something if blacs is in manual mode (as opposed to buffered)
    MODE_MANUAL = 1
    @define_state(MODE_MANUAL,True)  
    # when our button is clicked, we execute this function
    def on_click(self, btn):
        function_arg1, function_arg2 = "Hello", "Device" 
        self.logger.debug('Entering push button method')
        results = yield(self.queue_work('main_worker','do_work', function_arg1, function_arg2))        


    def initialise_workers(self):
        # Here we initialize the worker for the device. We can pass the worker properties from the connection table,
        # which can be accessed in the worker class by using self.name_of_variable
        connection_table = self.settings['connection_table']
        device = connection_table.find_by_name(self.device_name)

        # Create and set the primary worker
        self.create_worker(
            'main_worker',
            'user_devices.Rydberg.PrototypeDevice.blacs_workers.PrototypeDeviceWorker',
            {
                'name': device.properties['name'],
            },
        )
        self.primary_worker = 'main_worker'

