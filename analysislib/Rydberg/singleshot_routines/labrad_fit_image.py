import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from lyse import Run, data, path
from matplotlib.widgets  import RectangleSelector
from analysislib.Rydberg.analysis_utils.labrad_fitting_utils import (
    line_select_callback, 
    toggle_selector, 
    get_ROI,
    rotate_image)
from analysislib.Rydberg.analysis_utils.labrad_fitting_routines import find_atom_number, gaussian
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning) 

COLOR = 'white'
mpl.rcParams['text.color'] = COLOR
mpl.rcParams['axes.labelcolor'] = COLOR
mpl.rcParams['xtick.color'] = COLOR
mpl.rcParams['ytick.color'] = COLOR


# Get the pandas series with all of the globals etc. for this shot
ser = data(path)

# Get the Run instance with all of the shot's acquired data, such as
# images, traces, and results from analysis.
run = Run(path)

atoms_image = run.get_image('basler', 'CMOT', 'atoms')
atoms_image[atoms_image == 0] = 1

no_atoms_image = run.get_image('basler', 'CMOT', 'no_atoms')
no_atoms_image[no_atoms_image == 0] = 1

divided_image = atoms_image/no_atoms_image
# divided_image[divided_image == np.inf] = 1
# divided_image[np.isnan(divided_image)] = 1
# divided_image[divided_image == 0] = 1
# divided_image = np.clip(divided_image, 0, 1)

fig = plt.figure(constrained_layout=True)

fig.patch.set_facecolor('xkcd:black')
gs = fig.add_gridspec(3, 3)
image_axis = fig.add_subplot(gs[0:2, 0:2])
image_axis.spines['left'].set_color(COLOR)       
image_axis.spines['bottom'].set_color(COLOR) 
# drawtype is 'box' or 'line' or 'none'
toggle_selector.RS = RectangleSelector(image_axis, line_select_callback,
                                       drawtype='box', useblit=True,
                                       button=[1, 3],  # don't use middle button
                                       minspanx=5, minspany=5,
                                       spancoords='pixels',
                                       interactive=True)
plt.connect('key_press_event', toggle_selector)

x1,y1,x2,y2 = get_ROI()

if -1 not in (x1, y1, x2, y2):
    image_ROI = divided_image[x1:x2, y1:y2]
    atom_number, offset, height, x, y, width_x, width_y = find_atom_number(image_ROI)
else:
    image_ROI = divided_image
    atom_number = 0

plot_img = image_axis.imshow(divided_image, cmap=plt.get_cmap('plasma'))
#fig.colorbar(plot_img, ax=image_axis)
print("Atom Number: {:.3E}".format(atom_number))
                    
fit = gaussian(*[offset, height, x, y, width_x, width_y])
image_fit = fit(*np.indices(divided_image.shape))

horizontal_axis = fig.add_subplot(gs[2, 0:2], sharex=image_axis)
horizontal_axis.set_facecolor('xkcd:black')
horizontal_axis.spines['left'].set_color(COLOR)       
horizontal_axis.spines['bottom'].set_color(COLOR) 

x_points = np.arange(divided_image.shape[1])
horizontal_axis.scatter(x_points, np.log(divided_image).sum(axis=0), s=1, c='y')
horizontal_axis.plot(x_points, image_fit.sum(axis=0), c='r')

vertical_axis = fig.add_subplot(gs[0:2, 2], sharey=image_axis)
vertical_axis.set_facecolor('xkcd:black')
vertical_axis.spines['left'].set_color(COLOR)       
vertical_axis.spines['bottom'].set_color(COLOR) 

y_points = np.arange(divided_image.shape[0])
vertical_axis.scatter(np.log(divided_image).sum(axis=1), y_points, s=1, c='y')
vertical_axis.plot(image_fit.sum(axis=1), y_points, c='r')
vertical_axis.invert_xaxis()



text_axis = fig.add_subplot(gs[2, 2])
text_axis.set_axis_off()
text_axis.text(0, 0.5, "Atom Number: {:.3E}".format(atom_number))
