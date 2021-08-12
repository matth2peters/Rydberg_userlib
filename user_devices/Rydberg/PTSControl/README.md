# Explanation

This contains the code to control FPGAs that in turn control our PTS frequencies using the pins on the back. The communication between FPGA and PTS is done using BCD format, and the communication between the PC and the FPGA uses the Opal Kelly (ok) front panel library. These are not currently well understood in our lab and much of the worker code is legacy code from labrad 