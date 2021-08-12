"""
### BEGIN NODE INFO
[info]
name = hrmprocessor
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

import ctypes, numpy, sys, os
import pickle
import psutil
from pathlib import Path


def initialize():
        
    # initialize HRM module
    sensl.HRM_GetDLLVersion.restype = ctypes.c_char_p
    dll_str = sensl.HRM_GetDLLVersion()
    print("HRM DLL Version %s" % dll_str)

    sensl.HRM_RefreshConnectedModuleList()
    num_mod = sensl.HRM_GetConnectedModuleCount()

    print("Found %d module(s)." % num_mod)

    handle_buf_type = ctypes.c_int*3
    handle_buf = handle_buf_type(0,0,0)

    # get handle to identify device in future communiations
    status = sensl.HRM_GetConnectedModuleList(ctypes.pointer(handle_buf))
    h = handle_buf[0]

    sb = ctypes.create_string_buffer(128)
    status = sensl.HRM_GetModuleIDRegister(h,sb)

    id_str = ''
    for i in sb:
        id_str += i

    srr = ctypes.c_ushort(0)

    status = sensl.HRM_GetSoftwareRevisionRegister(h,ctypes.byref(srr))

    print("Module ID is %s; FPGA Vers. 0x%x" % (id_str,srr.value))

    status_buf = ctypes.c_ushort(0)
    status3 = sensl.HRM_GetStatusRegister(h, ctypes.byref(status_buf))
    print("Status before setting Frequency")
    print(repr(status_buf.value))

    status = sensl.HRM_SetFrequencySelectionRegister(h,  0x9999)

                
    status3 = sensl.HRM_GetStatusRegister(h, ctypes.byref(status_buf))
    print("Status after setting Frequency")
    print(repr(status_buf.value))


    sys.stdout.flush()

    reset_vars()

    
    ################ Variables for reading
def reset_vars(self):
    max_read_size = 16*16*1024
    act_read_size = ctypes.c_ulong(0)
    
    read_buf_type = ctypes.c_ulong*max_read_size
    read_buf = read_buf_type()
    to_save = []

    nCh = 4
    
    last_tt = numpy.zeros((nCh,2),dtype=ctypes.c_ulong)
    
    first_cycle = numpy.zeros((nCh,))
    
    times = [[],[],[],[]]
    
    last_gate = numpy.zeros((nCh,),dtype=ctypes.c_double)
    num_gates_global = numpy.zeros((nCh,),dtype=ctypes.c_ulong)
    num_cycles = numpy.zeros((nCh,),dtype=ctypes.c_ulong)
    num_gates_cycle = numpy.zeros((nCh,),dtype=ctypes.c_ulong)
    
    num_gates_arr = [ [], [], [], [] ]

    proc_output = []
    
    ch_buf = ctypes.c_char()
    gap_buf = ctypes.c_double()
    
    
def setup(self,c,gate_time_mus,save_prefix): 
    reset_vars()
    save_prefix = save_prefix
    gate_time_mus = gate_time_mus         
    target_filesize_MB = 2
    

    max_file_num = 0
    if not os.path.exists(save_prefix):
                os.makedirs(save_prefix)   
    files = os.listdir(save_prefix)  
            
    for f in files:
        if int(f.split('.')[0])> max_file_num:
            max_file_num = int(f.split('.')[0]) + 1
    
def acquire(self, c):
    tt_mode = ctypes.c_ushort(1)
    status = sensl.HRM_RunFifoTimeTagging(h, ctypes.c_ushort(0x5555), ctypes.c_ushort(0), tt_mode)

def stop(self, c): 
    #status = sensl.HRM_SetModeBitsRegister(h, 0x0030)
    output_chs = numpy.array( [x[0] for x in proc_output],dtype=ctypes.c_ubyte)
    output_times = numpy.array( [x[1] for x in proc_output],dtype=ctypes.c_double)
    output_gates = numpy.array( [x[2] for x in proc_output],dtype=ctypes.c_ushort)
    output_cycles = numpy.array( [x[3]for x in proc_output],dtype=ctypes.c_ushort)
    output_dict =  { 'ch':output_chs,
                        'times': output_times,
                        'gates': output_gates,
                        'cycles': output_cycles}    
                                
    if not os.path.exists(save_prefix):
        os.makedirs(save_prefix)   
    files = os.listdir(save_prefix)  
    max_file_num = 0
    for f in files:
        if int(f.split('.')[0])>= max_file_num:
            max_file_num = int(f.split('.')[0]) + 1
    with open(save_prefix +'\\'+str(max_file_num)+ '.pkl', 'wb') as f:
            pickle.dump(output_dict, f, pickle.HIGHEST_PROTOCOL)

    proc_output = []
                
def read(self, c):      
    mem_prog_buf = ctypes.c_ulong(0)
    status_buf = ctypes.c_ushort(0)
                
    #HRM_STATUS WINAPI HRM_GetWriteCountRegister(HANDLE handle, ULONG *wrrData)
    status2 = sensl.HRM_GetWriteCountRegister(h, ctypes.byref(mem_prog_buf) )
    print(repr(mem_prog_buf.value))        
    status3 = sensl.HRM_GetStatusRegister(h, ctypes.byref(status_buf))
    print(repr(status_buf.value))

        
    status = sensl.HRM_GetFifoData(h,
                                    ctypes.c_ushort(1),
                                    max_read_size,
                                    ctypes.byref(act_read_size),
                                    ctypes.byref(read_buf)
                                    )
    
    status = sensl.HRM_SetRoutingResetRegister(h, ctypes.c_ushort(0))
    

def process(self, c, cycle): 
    if act_read_size.value > 0:
        read_buf = read_buf[0:act_read_size.value]
        act_read_size = ctypes.c_ulong(0)
        buflen = len(read_buf)
        print(buflen)
        
        ptr = 0
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')                
        while ptr < buflen:
            micro = read_buf[ptr]
            macro = read_buf[ptr+1]
            ch = micro & 0b11
            ptr += 2
            
            status = sensl.HRM_GetTimeTagGap(ctypes.c_ulong(last_tt[ch][1]),
                                            ctypes.c_ulong(last_tt[ch][0]),
                                            ctypes.c_ulong(macro),
                                            ctypes.c_ulong(micro),
                                            ctypes.byref(ch_buf),
                                            ctypes.byref(gap_buf)
                                            )
            
            
                
            last_tt[ch][1] = macro
            last_tt[ch][0] = micro
            

            
            times[ch].append(1e-6 * gap_buf.value) # convert from ps to us
            

        for ch in xrange(nCh):
            if times[ch] != []:
                gate = 1
                time_temp = numpy.array(times[ch])
                times[ch] = []
                #Assuming the first click is a fake click and using the known gate period to define gates
                time_cumulative = 0
                for i in xrange(len(time_temp)-1):
                    time_cumulative += time_temp[i+1]
                    if time_cumulative >= gate_time_mus:
                        time_cumulative = 0
                        gate+=1
                        if gate >= 1600:
                            break
                    else:
                        proc_output.append( (ch, time_cumulative, gate, cycle) )
                    
        print(str(len(proc_output)/(target_filesize_MB*1024*1024/25.0) *100.0) + ' %')
        if len(proc_output) > target_filesize_MB*1024*1024/25:                
            output_chs = numpy.array( [x[0] for x in proc_output])
            output_times = numpy.array( [x[1] for x in proc_output])
            output_gates = numpy.array( [x[2] for x in proc_output])
            output_cycles = numpy.array( [x[3] for x in proc_output])
            output_dict =  { 'ch':output_chs,
                                'times': output_times,
                                'gates': output_gates,
                                'cycles': output_cycles}    
            
            
            with open(save_prefix +'\\'+str(max_file_num)+ '.pkl', 'wb') as f:
                    pickle.dump(output_dict, f, pickle.HIGHEST_PROTOCOL)
            max_file_num += 1
            print('$$$$$$$$ - Saved !!!!!!!')
        
            proc_output = []


    
                                        
            

if __name__ == "__main__":
    pid = os.getpid()
    py = psutil.Process(pid)


    sensl = ctypes.WinDLL('C:\\Program Files (x86)\\sensL\\HRM-TDC\\HRM_TDC DRIVERS\\HRMTimeAPI.dll')#'C:\Program Files (x86)\sensL\HRM-TDC\HRMTimeAPI.dll')
    initialize()


