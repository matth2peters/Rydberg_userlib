import numpy as np
import scipy.optimize

def gaussian(offset, height, center_x, center_y, width_x, width_y):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda x,y: offset+height*np.exp(
                -(((x-center_x)/width_x)**2+((y-center_y)/width_y)**2)/2)
                				

def moments(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution by calculating its
    moments """
    height = data.min()
    offset = data.max() - data.min()
    total = data.sum()
    X, Y = np.indices(data.shape)
    x = (X*data).sum()/total
    y = (Y*data).sum()/total
    col = data[:, int(y)]
    width_x = np.sqrt(np.abs(((np.arange(col.size)-y)**2*col).sum()/col.sum()))
    row = data[int(x), :]
    width_y = np.sqrt(np.abs(((np.arange(row.size)-x)**2*row).sum()/row.sum()))  

    return offset, height, x, y, np.abs(width_x), np.abs(width_y)

def fitgaussian(data):
    """Returns (offset, height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution found by a fit"""
    #
    data[np.isnan(data)] = 1
    data[np.isinf(data)] = 1
    params = moments(data)
    errorfunction = lambda p: np.ravel(gaussian(*p)(*np.indices(data.shape)) -
                                    data)
    #return params
    p, success = scipy.optimize.leastsq(errorfunction,params, maxfev = 300)
    return p
    
    

def find_atom_number(data_roi):

    TOP_MAG = 4.0/(10.0) # we are using a 10cm/15cm telescope for the top camera SC 2019/03/25  *)
    SIDE_MAG = 3.0/10.0 # we are using a 3cm/25cm telescope for the top camera SC 2019/03/25  *)
    ANDOR_MAG = 1.0 # 1.0/4.0 # we will use x4 magnification for Andor camera TS 2020/07/29
    CROSS_SECTION = 0.29 #micro meter ^2
    BASLER_PIXEL_RATIO = 3.45 #micrometer / pixel

    offset, height, x, y, width_x, width_y = fitgaussian(np.log(data_roi))
    atom_number = float(round(2*np.pi*(BASLER_PIXEL_RATIO**2/CROSS_SECTION)*(SIDE_MAG**2) * np.abs(height)* np.abs(width_x)* np.abs(width_y),0))

    return atom_number, offset, height, x, y, np.abs(width_x), np.abs(width_y)
        
    



        
            
            
            
                
         
        

