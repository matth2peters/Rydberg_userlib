import os
import cv2
from pathlib import Path
import pandas as pd
from lyse import routine_storage

PARAMETERS_PATH = os.path.dirname(os.path.abspath(__file__))

def line_select_callback(eclick, erelease):
    'eclick and erelease are the press and release events'
    x1, y1 = eclick.xdata, eclick.ydata
    x2, y2 = erelease.xdata, erelease.ydata
    print("ROI: (%3.2f, %3.2f) --> (%3.2f, %3.2f)" % (x1, y1, x2, y2))
    with open(PARAMETERS_PATH+ r'\parameter_files\labrad\roi_selection.txt', 'w') as f:
        f.write('x1,y1,x2,y2\n')
        f.write('{:.0f},{:.0f},{:.0f},{:.0f}'.format(x1, y1, x2, y2))

def get_ROI():
    if os.path.exists(PARAMETERS_PATH+ r'\parameter_files\labrad\roi_selection.txt'):

        with open(PARAMETERS_PATH+ r'\parameter_files\labrad\roi_selection.txt', 'r') as f:
            f.readline() # ignore first line
            x1, y1, x2, y2 = f.readline().split(',')

    else:
        x1, y1, x2, y2 = -1, -1, -1, -1

    return int(x1), int(y1), int(x2), int(y2)


def toggle_selector(event):
    print(' Key pressed.')
    if event.key in ['Q', 'q'] and toggle_selector.RS.active:
        print(' RectangleSelector deactivated.')
        toggle_selector.RS.set_active(False)
    if event.key in ['A', 'a'] and not toggle_selector.RS.active:
        print(' RectangleSelector activated.')
        toggle_selector.RS.set_active(True)

def rotate_image(image, deg):
    # load the image and show it
    image = cv2.imread(image)
    #cv2.imshow("Original", image)
    # grab the dimensions of the image and calculate the center of the
    # image
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    # rotate our image by 45 degrees around the center of the image
    M = cv2.getRotationMatrix2D((cX, cY), deg, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h))
    #cv2.imshow("Rotated by 45 Degrees", rotated)
    return rotated

def read_spcm_continuous_monitor(path):
    run_folder = str(Path(path).parent)
    counter_file = str(Path.joinpath(run_folder, 'count_record.txt'))
    
    if os.path.exists(counter_file):
        data = pd.read_csv(counter_file)
    else:
        data = None
        with open(counter_file, 'w') as f:
            f.write('run,counts\n')

    return data

def write_spcm_continuous_monitor(path, df):
    run_folder = str(Path(path).parent)
    counter_file = str(Path.joinpath(run_folder, 'count_record.txt'))
    data = pd.to_csv(counter_file) #,mode='w+'

    return data
        