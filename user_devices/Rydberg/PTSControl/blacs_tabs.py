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
from PyQt5.QtWidgets import QComboBox, QGridLayout, QLabel
from pathlib import Path

class PTSControlTab(DeviceTab):
    def initialise_GUI ( self ):
        """
        Initializes the GUI tab for the agilent
        """


        
        # pull the layout of the tab so that we can place widgets in it
        layout = self.get_tab_layout()

        # Get properties from connection table.
        device = self.settings['connection_table'].find_by_name(
            self.device_name
        )

        self.device_serial = device.properties['device_serial']
        # connect the selections in the combobox to the path to the bit file
        self.path_dictionary = device.properties['path_dictionary']

        # Make space for error messages
        error_row = QGridLayout()
        error_message = QLabel()
        error_message.setText("Error Message: ")
        error_message.setAlignment(Qt.AlignLeft)
        error_row.addWidget(error_message, 0, 0)

        self.PTS_error_message_contents = QLabel()
        self.PTS_error_message_contents.setText("No Error")
        self.PTS_error_message_contents.setAlignment(Qt.AlignLeft)
        error_row.addWidget(self.PTS_error_message_contents, 0, 1)
        layout.addLayout(error_row)

        # keep a dictionary of all the buttons
        self.button = {}
        
        # Freq textbox and label
        set_freq_row = QGridLayout()

        freq_label = QLabel()
        freq_label.setText("Frequency Set (MHz): ")
        freq_label.setAlignment(Qt.AlignLeft)
        set_freq_row.addWidget(freq_label, 0, 0)

        self.freq_textbox = QLineEdit()
        set_freq_row.addWidget(self.freq_textbox, 0, 1)


        self.button["set_freq"] = QPushButton()
        self.button["set_freq"].setText("Set Frequency")
        self.button["set_freq"].setStyleSheet("border :1px solid black")
        set_freq_row.addWidget(self.button["set_freq"], 0, 2)
        self.button["set_freq"].clicked.connect(self.set_frequency_worker)

        layout.addLayout(set_freq_row)

        # Get Frequency button and label
        get_freq_row = QGridLayout()

        get_freq_label = QLabel()
        get_freq_label.setText("Frequency (MHz): ")
        get_freq_label.setAlignment(Qt.AlignLeft)
        get_freq_row.addWidget(get_freq_label, 0, 0)

        self.current_freq = QLabel()
        self.current_freq.setText("None")
        self.current_freq.setAlignment(Qt.AlignLeft)
        get_freq_row.addWidget(self.current_freq, 0, 1)


        self.button["get_freq"] = QPushButton()
        self.button["get_freq"].setText("Get Frequency")
        self.button["get_freq"].setStyleSheet("border :1px solid black")
        get_freq_row.addWidget(self.button["get_freq"], 0, 2)
        self.button["get_freq"].clicked.connect(self.get_frequency_worker)

        layout.addLayout(get_freq_row)

        # Upload BIT files to FPGA
        bit_row = QGridLayout()

        bit_label = QLabel()
        bit_label.setText("Bit File")
        bit_label.setAlignment(Qt.AlignLeft)
        bit_row.addWidget(bit_label, 0, 0)

        self.bit_combobox = QComboBox()
        self.bit_combobox.addItem("Fast Ramp Up")
        self.bit_combobox.addItem("Fast Ramp Down")
        self.bit_combobox.addItem("Slow Control")
        bit_row.addWidget(self.bit_combobox, 0, 1)


        self.button["upload_bit"] = QPushButton()
        self.button["upload_bit"].setText("Upload Bit")
        self.button["upload_bit"].setStyleSheet("border :1px solid black")
        bit_row.addWidget(self.button["upload_bit"], 0, 2)
        self.button["upload_bit"].clicked.connect(self.upload_bit_file_worker)

        layout.addLayout(bit_row)


    MODE_MANUAL = 1
    @define_state(MODE_MANUAL,True)  
    def upload_bit_file_worker(self, btn):
        """On a button press, upload the file selected in the combobox to the FPGA via the worker
        """

        self.logger.debug('entering upload bit file button method')
        print("Uploading file: {}".format(self.bit_combobox.currentText()))
        path_file = self.path_dictionary[str(self.bit_combobox.currentText())]


        error_output = yield(self.queue_work('main_worker','upload_bit_file', path_file))

        self.PTS_error_message_contents.setText(str(error_output))


    @define_state(MODE_MANUAL,True)  
    def get_frequency_worker(self, btn):
        """On a button press, get the current frequency from the FPGA in MHz
        """
        freq_MHz = yield(self.queue_work('main_worker','get_frequency'))

        self.current_freq.setText(str(round(freq_MHz, 3)))
        



    @define_state(MODE_MANUAL,True)  
    def set_frequency_worker(self, btn):
        """On a button press, upload the file selected in the combobox to the FPGA via the worker
        """
        try:
            to_set_frequency_MHz = float(self.freq_textbox.text())
        except:
            raise RuntimeError("Please choose a valid frequency.")
        yield(self.queue_work('main_worker','set_frequency', to_set_frequency_MHz))
        


    def initialise_workers(self):
        connection_table = self.settings['connection_table']
        device = connection_table.find_by_name(self.device_name)

        # Create and set the primary worker
        self.create_worker(
            'main_worker',
            'user_devices.Rydberg.PTSControl.blacs_workers.PTSControlWorker',
            {
                'device_serial': self.device_serial
            },
        )
        self.primary_worker = 'main_worker'

