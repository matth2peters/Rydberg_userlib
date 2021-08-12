#
# Server for setting frequency on Opal Kelly FPGAs that control PTS3200 synthesizer
#
#
# JDT 7/2015
# Modified Aditya 7/2016
#

"""
### BEGIN NODE INFO
[info]
name = pts
version = 1.0
description =
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

from labrad import types as T
from labrad.server import LabradServer, setting
import ctypes
import numpy as np
import datetime as dt
import time


def initServer(self):
    self.lastStepTime = dt.datetime.now()
    self.serials = ['10440000KE','10440000K8'] #[probe, control]

    path_to_lib = r'B:\Dropbox (MIT)\Our Programs\New Labrad Setup\PyLabradControl\Servers\Header+Bit files\okFrontPanel.dll'
    self.oklib = ctypes.WinDLL(path_to_lib)
    
    self.freqStepSize = T.Value(1.0,'MHz')#a loop takes ~ 3 ms. This value should be safe.       
    
    #Bit file paths
    self.slowBIT = 'Header+Bit files\\slowcontrol.bit'
    self.fastUPBIT = 'Header+Bit files\\fastcontrolUP.bit'
    self.fastDNBIT = 'Header+Bit files\\fastcontrolDN.bit'        
    
    self.hndProbe = self.oklib.okFrontPanel_Construct()
    self.hndControl = self.oklib.okFrontPanel_Construct()
    
    self.nDev = self.oklib.okFrontPanel_GetDeviceCount(self.hndProbe)
    
    buf = ctypes.create_string_buffer(128)

    self.serials_in = []
    
    for i in range(self.nDev):
        self.oklib.okFrontPanel_GetDeviceListSerial(self.hndProbe,i,buf)
        self.serials_in.append(buf.value)
    
    print "Found %d devices with serials %s" % (self.nDev, repr(self.serials_in))
    print "Expected serials %s" % repr(self.serials)
    self.connect(0, 'Probe')
    self.connect(0, 'Control')
    
def stopServer(self):
    if self.hndProbe != 0:
        self.oklib.okFrontPanel_Destruct(self.hndProbe)
    
    elif self.hndControl != 0:
        self.oklib.okFrontPanel_Destruct(self.hndControl)
    
@setting(9, "connect", device='s')
def connect(self, c, device):
    """ establish connection to Opal Kelly FPGAs that control PTS synth"""
    if (device=='Probe' or device =='probe'):
        deviceStr = self.serials[0]
        if self.hndProbe == 0:
            self.hndProbe = self.oklib.okFrontPanel_Construct()
        self._check(self.oklib.okFrontPanel_OpenBySerial(self.hndProbe, deviceStr))
    
    elif (device =='Control' or device == 'control'):
        deviceStr = self.serials[1] 
        if self.hndControl == 0:
            self.hndControl = self.oklib.okFrontPanel_Construct()
        self._check(self.oklib.okFrontPanel_OpenBySerial(self.hndControl, deviceStr))
    
@setting(7, "disconnect", device='s')
def disconnect(self, c, device):
    """ Disconnect Opal Kelly FPGAs that control PTS synth"""
    if (device=='Probe' and self.hndProbe != 0):
        self.oklib.okFrontPanel_Destruct(self.hndProbe)
        self.nDev -= 1
    
    elif (device =='Control' and self.hndControl != 0):
        self.oklib.okFrontPanel_Destruct(self.hndControl)
        self.nDev -= 1
        

@setting(8, "uploadBIT", device='s', mode ='s')
def uploadBIT(self, c, device, mode):
    """ Upload appropriate BIT file to Opal Kelly FPGAs that control PTS synth"""
    if (device == 'Probe' or device =='probe'):
        if mode == 'slow':
            path = self.slowBIT 
        elif mode == 'fastUP':
            path = self.fastUPBIT
        elif mode == 'fastDN':
            path = self.fastDNBIT
        else :
            print "Error: mode not valid" % (mode)
        self._check(self.oklib.okFrontPanel_LoadDefaultPLLConfiguration(self.hndProbe))
        self._check(self.oklib.okFrontPanel_ConfigureFPGA(self.hndProbe, path))
        
    elif (device == 'Control' or device == 'control'):
        if mode == 'slow':
            path = self.slowBIT 
        elif mode == 'fastUP':
            path = self.fastUPBIT
        elif mode == 'fastDN':
            path = self.fastDNBIT
        else :
            print "Error: mode not valid" % (mode)
        self._check(self.oklib.okFrontPanel_LoadDefaultPLLConfiguration(self.hndControl))
        self._check(self.oklib.okFrontPanel_ConfigureFPGA(self.hndControl, path))
        
                
@setting(3,"get_num",returns="w")
def get_num(self,c):
    """ returns found number of OK devices """
    return self.nDev

@setting(2,"get_freq",device="s",returns="v[MHz]")
def get_freq(self,c,device):
    """ get freq. of device """
    if (device == 'Probe' or device =='probe'):
        self.oklib.okFrontPanel_UpdateWireOuts(self.hndProbe)
        self.oklib.okFrontPanel_GetWireOutValue.restype = ctypes.c_uint32
        val20 = self.oklib.okFrontPanel_GetWireOutValue(self.hndProbe,ctypes.c_int32(0x20))
        val21 = self.oklib.okFrontPanel_GetWireOutValue(self.hndProbe,ctypes.c_int32(0x21))
    
    elif (device == 'Control' or device == 'control'):
        self.oklib.okFrontPanel_UpdateWireOuts(self.hndControl)
        self.oklib.okFrontPanel_GetWireOutValue.restype = ctypes.c_uint32
        val20 = self.oklib.okFrontPanel_GetWireOutValue(self.hndControl,ctypes.c_int32(0x20))
        val21 = self.oklib.okFrontPanel_GetWireOutValue(self.hndControl,ctypes.c_int32(0x21))
    else :
        print "Error: device not Valid %s. Input Probe or Control" % (device)
        return T.Value(0,'MHz')
    
    
    #print "val20,val21 = %d,%d" % (val20,val21)
    
    # this encoding is totally insane, but apparently the way the FPGA is written
    # is that these numbers should be converted into hex strings and then interpreted
    # as base-10 strings.
    
    # So, a frequency of 1234.5678 MHz becomes 12345678 * 100 Hz
    # converted into string '12345678'
    # then split into two strings '1234', '5678'
    # then these strings are interpreted as hex numbers 0x1234, 0x5678
    # and these two hex numbers are sent to the card.
    # To retrieve the frequency here, we do this in reverse.
    
    # make hex string
    lowerhex = format(val20,'x')
    upperhex = format(val21,'x')
    
    # re-interpret as decimal string. This could give error if abcdef appears in string...
    lowerint = int(lowerhex,10)
    upperint = int(upperhex,10)
    
    freqMHz = lowerint*0.0001 + upperint
    
    return T.Value(freqMHz,'MHz')
    

@setting(10,"setup_fast_scan",device='s', min_freq='v[MHz]', max_freq='v[MHz]', step='v[MHz]')
def setup_fast_scan(self,c,device, min_freq, max_freq, step):
    #Define Ramping parameters here....
    num_cycles_between_ramp_steps = 1e2
    ramp_step =  0.8/8 #MHz
    
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
    
    if (device == 'Probe' or device =='probe'):
        # 0xFFFF is a mask
        # 0x00 -> min freq LSB, 0x01 -> min freq MSB
        # 0x04 -> max freq LSB, 0x05 -> max freq MSB
        # 0x02 -> step up freq LSB, 0x03 -> step up freq MSB
        # 0x06 -> ramp dn freq LSB, 0x07 -> ramp dn freq MSB
        # 0x09 -> num_cycles_between_ramp_steps_LSB, 0x010 -> num_cycles_between_ramp_steps_MSB

        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x00), ctypes.c_uint16(min_freqLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x01), ctypes.c_uint16(min_freqMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x04), ctypes.c_uint16(max_freqLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x05), ctypes.c_uint16(max_freqMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x02), ctypes.c_uint16(stepLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x03), ctypes.c_uint16(stepMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x06), ctypes.c_uint16(ramp_stepLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x07), ctypes.c_uint16(ramp_stepMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x09), ctypes.c_uint16(num_cycles_between_ramp_steps_LSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x10), ctypes.c_uint16(num_cycles_between_ramp_steps_MSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_UpdateWireIns(self.hndProbe)
        
    
    elif (device == 'Control' or device == 'control'):
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x00), ctypes.c_uint16(min_freqLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x01), ctypes.c_uint16(min_freqMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x04), ctypes.c_uint16(max_freqLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x05), ctypes.c_uint16(max_freqMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x02), ctypes.c_uint16(stepLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x03), ctypes.c_uint16(stepMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x06), ctypes.c_uint16(ramp_stepLSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x07), ctypes.c_uint16(ramp_stepMSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x09), ctypes.c_uint16(num_cycles_between_ramp_steps_LSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x10), ctypes.c_uint16(num_cycles_between_ramp_steps_MSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_UpdateWireIns(self.hndControl)
    
    else :
        print "Error: device not Valid %s. Input Probe or Control" % (device)
        return T.Value(0,'MHz')
        
        
        

@setting(4,"set_freq",device='s',freq='v[MHz]')
def set_freq(self,c,device,freq):
    """ set freq. of device """
    
        #Finding the current Frequency
    currentFreqMHz = self.get_freq(c, device)['MHz'] 
    freqMHz = freq['MHz']
    print("Current frequency %f" %(currentFreqMHz))
    print("Set frequency %f" %(freqMHz))
    sign = np.sign(freqMHz - currentFreqMHz)
    a = dt.datetime.now()
    while np.abs(freqMHz - currentFreqMHz)  >  self.freqStepSize['MHz']:
        currentFreqMHz = currentFreqMHz + sign*self.freqStepSize['MHz']
        self.set_freq_help(device, currentFreqMHz)
    
    self.set_freq_help(device, freqMHz)
    
    b = dt.datetime.now()
    print("Total sweep time %f seconds" %((b-a).total_seconds()))

    
    
def set_freq_help(self, device, freqMHz):
    """ set freq. of device """    
    
    # convert to insane transmission format (see comment in get_freq)
    freq100Hz = int(round(freqMHz*10000))
    
    freq100HzStr = format(freq100Hz,'d')
    
    freqLSB = int(freq100HzStr[-4:],16)
    freqMSB = int(freq100HzStr[:-4],16)
    
    if (device == 'Probe' or device =='probe'):
        # this is from WireInParamsSlowScanONLYfreq.vi
        #0x04 -> freqLSB, 0x05 -> freqMSB, 0xFFFF is a mask.. can't find it in the API documentation, but is there in the LabView program

        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x05), ctypes.c_uint16(freqMSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x04), ctypes.c_uint16(freqLSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_UpdateWireIns(self.hndProbe)
        

        # 0x11 -> goToFreq
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x11), ctypes.c_uint16(1), ctypes.c_uint16(1))
        self.oklib.okFrontPanel_UpdateWireIns(self.hndProbe)
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndProbe, ctypes.c_uint8(0x11), ctypes.c_uint16(0), ctypes.c_uint16(1))
        self.oklib.okFrontPanel_UpdateWireIns(self.hndProbe)
    
    elif (device == 'Control' or device == 'control'):
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x05), ctypes.c_uint16(freqMSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x04), ctypes.c_uint16(freqLSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_UpdateWireIns(self.hndControl)
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x11), ctypes.c_uint16(1), ctypes.c_uint16(1))
        self.oklib.okFrontPanel_UpdateWireIns(self.hndControl)
        
        self.oklib.okFrontPanel_SetWireInValue(self.hndControl, ctypes.c_uint8(0x11), ctypes.c_uint16(0), ctypes.c_uint16(1))
        self.oklib.okFrontPanel_UpdateWireIns(self.hndControl)
    
    else :
        print "Error: device not Valid %s. Input Probe or Control" % (device)
        return T.Value(0,'MHz')
        
    
        
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
            
        raise RuntimeError('Opal Kelly failed with error %s'%(error_string))
    
if __name__ == "__main__":

