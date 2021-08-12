# User-defined devices

Each user-defined device requires 4 python files: register_classes.py, labscript_devices.py, blacs_tabs.py, and blacs_workers.py

## register_classes.py
defines the names of the classes/functions so that labscript can find them. It is not important to add anything to this file other than to ensure the names correspond correctly to the names of your device classes/runviewer parsers/etc.

## labscript_devices.py
defines the API for communicating with the device. Here, we first define how the device is instantiated in the connection table file. Usually, the device will inherit from either TriggerableDevice or IntermediateDevice, and we only need to define the '__init__' method, the 'generate_code' method, and any functionality for the device that will be called in a sequence/shot file. 

### '__init__' Method 
In the init method, we can pass in any important device parameters such as names, parent devices, time between triggers, etc.  This info is passed through a decorator

### 'generate_code' Method
This method tells labscript how to generate the code for the HDF file that is passed to the worker (see the worker class below). For example, in the Agilent 33250A class, we need to pass a list of commands to send to the AWG. These string commands are stored in the HDF file created by this method, and then the worker opens this HDF file to retrieve the commands

### Other Methods
At least one other method is necessary so that command over the device in the sequence is possible. For example, if we were making a custom AOM class, we would want to define a method to set the analog input voltage level for the AOM. This method would be called on the device instantiated in the connection table. If the name of the method was 'set_frequency' and our instantiated device was 'repump_AOM', in the sequence file we would call 'repump_AOM.set_frequency(5 * MHz)' to interact with the device. 

## blacs_tabs.py
This file is responsible for implementing the GUI and creating the worker that communicates with the device. It has the method 'initialise_GUI' (make sure you spell it the British way), which will display the device status and allow sending commands to it manually with buttons, etc. It also has the 'initialise_workers' method, which instantiates the worker that actually communicates with the device. See Agilent33250A for an example.

It is important that you do not try to communicate directly with the device using this class. This will throw errors and mess up the threads between different processes. If you would like to communicate with the worker, use the 'yield(self.queue_work, ...)' instead of return as in the Agilent33250A device 'on_click' function. For example, in the Agilent class, the worker is told to set the frequency when a button is pressed and BLACS is in manual mode. 

## blacs_workers.py
This is the workhorse and is responsible for directly communicating with the device in question. It can, for example, send serial commands to the device. It has numerous functions that are overidden, most of which can be ignored and set to return 'True'.

### 'transition_to_...'
These functions tell the worker to do something when transition between states of the state machine. For example, when transitioning to manual from buffered, you may want to update some settings on your device. 


### 'abort_...'
similar to above, tell your worker what to do if some transition is aborted 

### 'program_manual'
This function automatically updates the device based on the values in the GUI. As an example, the NI analog cards are automatically/instantly updated with this methods whenever the output voltage in the GUI is changed

### 'shutdown'
Called whenever BLACS is exited. Here you should ensure you close your serial connections, TCP ports, etc.

### 'init'
This is where device-specific imports are declared and the device in initialized. Here you may want to ensure the device is sent certain settings, the serial port is opened, etc.