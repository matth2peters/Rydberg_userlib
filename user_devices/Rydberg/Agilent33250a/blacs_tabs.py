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

class Agilent33250aTab(DeviceTab):
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

        self.com_port = device.properties['com_port']
        self.baud_rate = device.properties['baud_rate']
        self.device_id = device.properties['device_ID']
        self.RS_232 = device.properties['RS_232']

        # various widgets we will put in the layout
        self.freq_textbox = {}
        self.amp_textbox = {}
        self.offset_textbox = {}
        self.button = {}

        label_w = 150
        label_h = 25

        # Make space for error messages
        error_row = QGridLayout()
        error_message = QLabel()
        error_message.setText("Error Message: ")
        error_message.setAlignment(Qt.AlignLeft)
        error_row.addWidget(error_message, 0, 0)

        self.AWG_error_message_contents = QLabel()
        self.AWG_error_message_contents.setText("No Error")
        self.AWG_error_message_contents.setAlignment(Qt.AlignLeft)
        error_row.addWidget(self.AWG_error_message_contents, 0, 1)
        layout.addLayout(error_row)


        # for each channel, make a new row to put the label, editable textbox, and button to send the contents of the text box
        cur_row = QGridLayout()
        
        # Freq textbox and label
        freq_label = QLabel()
        freq_label.setText("Gated Sine Freq (Hz)")
        freq_label.setAlignment(Qt.AlignLeft)
        cur_row.addWidget(freq_label, 0, 0)

        self.freq_textbox["gated_sine"] = QLineEdit()
        self.freq_textbox["gated_sine"].setAlignment(Qt.AlignRight)
        cur_row.addWidget(self.freq_textbox["gated_sine"], 0, 1)

        # amplitude textbox and label
        amp_label = QLabel()
        amp_label.setText("Amplitude (V)")
        amp_label.setAlignment(Qt.AlignLeft)
        cur_row.addWidget(amp_label, 0, 2)

        self.amp_textbox["gated_sine"] = QLineEdit()
        self.amp_textbox["gated_sine"].setAlignment(Qt.AlignRight)
        cur_row.addWidget(self.amp_textbox["gated_sine"], 0, 3)

        # offset textbox and label
        off_label = QLabel()
        off_label.setText("Offset (V)")
        off_label.setAlignment(Qt.AlignLeft)
        cur_row.addWidget(off_label, 0, 4)

        self.offset_textbox["gated_sine"] = QLineEdit()
        self.offset_textbox["gated_sine"].setAlignment(Qt.AlignRight)
        cur_row.addWidget(self.offset_textbox["gated_sine"], 0, 5)


        self.button["gated_sine"] = QPushButton()
        self.button["gated_sine"].setText("Send gated sine")
        self.button["gated_sine"].setStyleSheet("border :1px solid black")
        cur_row.addWidget(self.button["gated_sine"], 0, 6)

        # # this is a trashy way to make the layout look less stretched
        # for i in range(0, 10):
        #     cur_row.addWidget(QLabel(), 0, i+5)

        layout.addLayout(cur_row)

        # we add the buttons to a button group so that we can determine which button was pressed
        self.btn_grp = QButtonGroup()
        self.btn_grp.setExclusive(True)
        for button in self.button.values():
            self.btn_grp.addButton(button)

        # when one of the buttons in the button group is pressed, execute on_click method (below)
        self.btn_grp.buttonClicked.connect(self.on_click)

    MODE_MANUAL = 1
    @define_state(MODE_MANUAL,True)  
    def on_click(self, btn):
        """On a button press, send the corresponding textbox contents to the AWG

        Args:
            btn ([type]): which of the buttons were pressed
        """
        self.logger.debug('entering AWG button method')
        command_list = []

        # if the gated sine button was pressed ...
        if "gated sine" in btn.text():
            # try to get the float value from the textbox, check to see if the contents are a float, then set the DDS channel
            try:
                set_freq = float(self.freq_textbox["gated_sine"].text())
                set_amp = float(self.amp_textbox["gated_sine"].text())
                set_off = float(self.offset_textbox["gated_sine"].text())


            except:
                print("PLEASE ENTER VALID FLOATS")
                self.logger.debug("PLEASE ENTER VALID FLOATS")
                # exit function
                return

            
            command_list.append(r':OUTP OFF')
            command_list.append(r':FUNC SIN')
            command_list.append(r':VOLT %.4f V' % set_amp)  # Vpp
            command_list.append(r':FREQ %.4f' % set_freq)  # Hz
            command_list.append(r':VOLT:OFFS %.4f V' % set_off) # Volts
            command_list.append(r':TRIG:SOUR EXT')
            command_list.append(r':TRIG:DEL MIN')
            command_list.append(r':TRIG:SLOP POS')
            command_list.append(r':OUTP:LOAD INF')
            command_list.append(r':BURS:STAT ON')
            command_list.append(r':BURS:MODE GAT')
            command_list.append(r':BURS:GATE:POL NORM')
            command_list.append(r':OUTP ON')

            error_output = yield(self.queue_work('main_worker','send_commands', command_list, self.RS_232))

            self.AWG_error_message_contents.setText(error_output)
            return


        


    def initialise_workers(self):
        connection_table = self.settings['connection_table']
        device = connection_table.find_by_name(self.device_name)

        # Create and set the primary worker
        self.create_worker(
            'main_worker',
            'user_devices.Rydberg.Agilent33250a.blacs_workers.Agilent33250aWorker',
            {
                'com_port': self.com_port,
                'baud_rate': self.baud_rate,
                'RS_232': self.RS_232
            },
        )
        self.primary_worker = 'main_worker'

