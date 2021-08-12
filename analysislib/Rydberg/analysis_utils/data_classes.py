from collections import defaultdict
from math import isclose
import os.path

import labscript_utils.h5_lock
import h5py
from pynput.keyboard import Key, Listener
from matplotlib import patches
import matplotlib.pyplot as plt
import cv2
import matplotlib as mpl
import numpy as np
np.seterr(divide='ignore', invalid='ignore') # ignore annoying division error for images
import scipy.constants

from lyse import Run, routine_storage
from analysislib.Rydberg.analysis_utils.fitting_routines import fit_gaussian_with_offset, gaussian, gaussian_with_offset
from lyse.dataframe_utilities import get_nested_dict_from_shot, asdatetime
from labscript_utils.connections import _ensure_str
from runmanager import get_shot_globals

# Set MATPLOTLIB params. This sets the figure size
DEFAULT_FIGURE_SIZE = (10.0, 9.0)
# Here we set the background to black and make everything else white so that it's easier to look at
COLOR = 'white'
mpl.rcParams['text.color'] = COLOR
mpl.rcParams['axes.labelcolor'] = COLOR
mpl.rcParams['xtick.color'] = COLOR
mpl.rcParams['ytick.color'] = COLOR
mpl.rcParams["axes.facecolor"] = COLOR
mpl.rcParams["figure.facecolor"] = 'black'


# Set some constants that should probably stored elsewhere but are needed
# for calculations here.
# D2 line wavelength in meters.
WAVELENGTH_D2 = 780.241209e-9  # meters.
# Resonant cross section for the D2 line.
SIGMA_0 = 3 * WAVELENGTH_D2**2 / (2 * np.pi)
# Mass of one rubidium 87 atoms in kg.
M87 = 1.443160e-25  # kg.
# Conversion between size in pixels and size in meters at the position of
# the atoms.
BASLER_PIXEL_RATIO = 3.45e-6 # meter / pixel.
BASLER_MAG = 3.0/10.0
BASLER_PIXEL_SIZE = BASLER_PIXEL_RATIO * BASLER_MAG  # meters.
# Correction to conversion factor between OD and atom number to account for
# the fact that we don't see the full cross section due to experimental
# imperfections. Stolen from Zak.
OD_TO_ATOM_NUMBER_CORRECTION = 2.57
# Conversion bewteen integrated OD and atom number, atoms per integrated
# optical depth.
OD_TO_ATOM_NUMBER = OD_TO_ATOM_NUMBER_CORRECTION * BASLER_PIXEL_SIZE**2 / SIGMA_0
# Conversion factor for calcuating temperatures. Multiply this factor by the
# square of a thermal cloud's size (sigma of its gaussian) in pixels and
# divide by the square of the time of flight in seconds. That will give the
# temperature in uK. The conversion comes from (1/2)mv**2 = (1/2)kT. Units
# of the conversion factor are uK*(s**2/pixel_length**2). The factor of 1e6
# is to convert K to uK.
TEMPERATURE_COEFF = BASLER_PIXEL_SIZE**2 * (M87 / scipy.constants.k) * 1e6



def group_by_function(object_list, grouping_function, *args, **kwargs):
    """Group objects by the results of applying grouping_function to them.

    This method applies grouping_function to each element in object_list, then
    puts all the objects which give the same return value into a list. A list of
    these lists is then returned, which one sublist for each different return
    value from grouping_function.

    This function is implemented using python's defaultdict class, which makes
    it scale nicely (linearly) with length of object_list. However, that means
    that the results returned by grouping_function must be valid python
    dictionary keys.

    Args:
        object_list (list): A list of elements which should be grouped. Any type
            is acceptable, as long as it is a valid input for grouping_function.
        grouping_function (function): A function that is applied to each element
            of object_list. Objects which give the same output when provided to
            grouping_function are then put together in one list, then a list of
            these lists is returned. No attempt is made to catch any errors
            thrown by grouping_function, so ensure that it behaves as desired
            when passed any element of object list. Additionally, the function
            must return a value that is hashable, i.e. a valid key for a python
            dictionary. This means that lists and numpy arrays are not
            acceptable, but tuples, strings, numbers, etc. are acceptable.
            Tuples created by calling tuple() on a list or numpy array are also
            acceptable.

    Returns:
        grouped_object_list (list of lists): A list of sublists, where each
            sublist has elements from object_list which all lead to the same
            value when passed to grouping_function. Each element of object_list
            is included in the output, and is in only one sublist.
    """
    # This defaultdict is like a normal dict, except that it will return an
    # empty list (instead of throwing a KeyError) if a value is requested for a
    # key that isn't in the defaultdict.
    groups = defaultdict(list)
    for object_ in object_list:
        # Append the object to the list of objects for which grouping_function
        # gives the same result. Note that this will append to an empty list if
        # the value is not an existing key in the defaultdict.
        key = grouping_function(object_, *args, **kwargs)
        groups[key].append(object_)

    # The values of the defaultdict are now the lists of objects which give the
    # same output for grouping_function, so we can extract and return them.
    grouped_object_list = groups.values()
    return grouped_object_list


def group_by_attributes(object_list, attribute_list):
    """Group objects by their values of certain attributes.

    This method retrieves the value of all of the attributes in attribute_list
    for each of the objects in object_list. It then puts all objects which have
    the same values for all of the attributes into a list together, then returns
    a list of these lists.

    This is implemented internally by a call to group_by_function(), so more
    information may be found in that function's docstring. As mentioned there,
    the values must be hashable, so when values are numpy arrays, they are
    converted to bytes before passing them to group_by_function() (the input
    object's attribute is NOT edited). It may be necessary to edit this code in
    the future to provide conversions for other nonhashable datatypes as well.

    Args:
        object_list (list): A list of elements which should be grouped. Any type
            is acceptable as long as they all have all of the attributes listed
            in attribute_list.
        attribute_list (list of str): A list of strings, each one specifying an
            attribute of the objects in object list which should have the same
            value in order for two objects to be put into the same list.

    Returns:
        grouped_object_list (list of lists): A list of sublists, where each
            sublist has elements from object_list which all have the same values
            for all of the attributes in attribute_list. Each element of
            object_list is included in the output, and is in only one sublist.
    """
    # Make a function that returns the values of the attributes in a tuple.
    def grouping_function(object_):
        # Get all the values corresponding to all of the attributes.
        value_list = [getattr(object_, attribute)
                      for attribute in attribute_list]
        # Numpy arrays aren't hashable and so can't be used a dict keys, so
        # we'll call to_bytes() on any numpy arrays.
        hashable_list = []
        for value in value_list:
            if isinstance(value, np.ndarray):
                hashable_list.append(value.tobytes())
            else:
                hashable_list.append(value)
        # And lists aren't hashable to we have to convert to a tuple.
        return tuple(hashable_list)

    # Group using that function
    grouped_object_list = group_by_function(object_list, grouping_function)
    return grouped_object_list


class Shot(Run):
    """A class for performing data analysis on individual shots.

    This class extends the functionality of the Lyse.Run class. It's primary
    difference is that it stores its results in the 'shot_results' group in the
    hdf5 file by default (rather than in a group named after whatever script
    created the instance) and includes some methods for data analysis, such as
    calculating the od_image and performing fits. It also saves results as
    attributes of itself, so that e.g. the atom number can be accessed as
    self.atom_number instead of having to use the get_result() method. The
    values for globals and some other columns present in the Lyse dataframe can
    also be accessed in the same manner.

    To ensure that all Shot instances created for a given hdf5 file can find the
    results from all of the others, their results are saved to the group
    'shot_results' in the hdf5 file (rather than a group named after the script
    that called the Shot analysis routines as would be default with Lyse). This
    is convenient because then a Shot class instance created in one script will
    immediately have access to results from a Shot class instance in another
    script without having to do any configuration. This also means that calling
    self.set_group() externally is probably a bad idea, as the Shot instance
    from one script won't be able to find the results from the Shot instance of
    another script (unless self.set_group() is called in both scripts with the
    same argument).

    Attributes:
        h5_path (str): The path to the hdf5 file (including the file name and
            extension) for the shot. This is the same path that you would pass
            to initialize a lyse.Run instance. In fact, it is passed to
            lyse.Run.__init__() so it serves the exact same purpose.
        globals (dict): The globals from the hdf5 file, as returned by
            runmanager.get_shot_globals(). They are stored in a dict where the
            keys are the names of the globals (as strings) and the values in the
            dict are the corresponding values of the globals. The values of
            these globals can be accessed through this dictionary, or more
            conveniently they can be accessed via dot notation as e.g.
            self.mot_duration. It is worth noting that the globals are gotten
            from runmanager.get_shot_globals() (rather than the get_globals()
            method inherited from lyse.Run) because that function does a better
            job of handling None and other data types.

    Some columns in the Lyse dataframe contain data that is neither from a
    global or the result of some analysis, such as the 'sequence' column. For
    convenience, the following properties are added to Shot instances to mirror
    the data in the LYse dataframe/

    Attributes from Lyse dataframe:
        sequence (str): The value in the sequence column of the Lyse dataframe.
            All shots from one press of 'Engage' in Runmanager get the same
            value for sequence, and this value is different than the one from
            any other press of 'Engage' in Runmanager.
        sequence_index (int): The value in the 'sequence_index' column of the
            Lyse dataframe
        labscript (str): The name of the labscript file that was used to
            generate the sequence. Note that this is simply the name of the
            file, not all of the text in the file.
        run_time (pandas.Timestamp): The value in the 'run time' column of the
            Lyse dataframe (note the change of a space to an underscore). This
            corresponds to the time at which BLACS actually ran the shot.
        run_number (int): An index that keeps track of what order shots from one
            sequence (i.e. click of 'Engage' in Runmanager) were run in (note
            the change of a space to an underscore). The first shot for one
            sequence has run_number 0, the second has run_number 1, etc.
        run_repeat (int):  The value in the 'run repeat' column of the Lyse
            dataframe (note the change of a space to an underscore).

    Below is a list of the results that are typically assigned to the shot
    instance as attributes during the analysis. More attributes may be available
    if other code does more analysis and saves its results to the shot instance
    or to the hdf5 file. They are categorized by which method calculates them.

    Result Attributes from self.process_image:
        od_image (np.array): A 2D image of the atomic cloud's optical depth.

        integrated_od (float): The total optical depth of the cloud integrated
            over the atom region.
        atom_number (float): The number of atoms in the cloud, calculated from
            self.integrated_od. Note that this isn't calculated by integrating
            the area under the fitted gaussian.

        horizontal_indices (np.array): A 1D array giving the indices of the
            pixels corresponding to the horizontal cross section.
        horizontal_cross_section (np.array): The integrated horizontal cross
            section of the atomic cloud. For the corresponding pixel indices,
            use self.horizontal_indices.
        vertical_indices (np.array):  A 1D array giving the indices of the
            pixels corresponding to the vertical cross section.
        vertical_cross_section (np.array): The integrated vertical cross section
            of the atomic cloud. For the corresponding pixel indices, use
            self.vertical_indices.

    Result Attributes from self.fit_gaussians:
        horizontal_center (float): The fitted center of the atomic cloud in the
            horizontal direction.
        horizontal_sigma (float): The fitted width of the atomic cloud in the
            horizontal direction. The width given is the standard deviation of
            the gaussian fit to the atomic cloud.
        horizontal_amplitude (float): The fitted gaussian amplitude of the
            cloud's horizontal cross section.
        horizontal_offset (float): The offset of the gaussian fit to the
            horizontal cross section.
        horizontal_temperature (float): The temperature of the cloud in the
            horizontal direction.

        vertical_center (float): The fitted center of the atomic cloud in the
            vertical direction.
        vertical_sigma (float): The fitted width of the atomic cloud in the
            vertical direction. The width given is the standard deviation of the
            gaussian fit to the atomic cloud.
        vertical_amplitude (float): The fitted gaussian amplitude of the cloud's
            vertical cross section.
        vertical_offset (float): The offset of the gaussian fit to the vertical
            cross section.
        vertical_temperature (float): The temperature of the cloud in the
            vertical direction.
    """

    def __init__(self, h5_path):
        """Create a Shot instance for analyzing data from one shot.

        Args:
            h5_path (str): The path to the hdf5 file (including the file name
                and extension) for the shot. This is the same path that you
                would pass to initialize a lyse.Run instance.
        """
        # Run the Run class's __init__().
        super().__init__(h5_path)

        # Set 'shot_results' as the default group when saving results.
        #self.set_group('shot_results')

        # Set self.globals. We'll use runmanager.get_shot_globals() rather than
        # the inherited Run.get_globals() because the former does a better job
        # of handling None and a few other data types.
        self.globals = get_shot_globals(h5_path)

        # Set some additional properties based on columns from Lyse dataframe
        # that aren't globals.
        # Calling lyse.dataframe_utilities.get_nested_dict_from_shot() is
        # somewhat inefficient because it loads a lot more data from the file
        # than we'll need here, but it's the same function that Lyse uses so
        # using it here ensures that we'll get the same results with the same
        # datatype, etc.. Below is code that uses it, which we've commented out
        # for now.
        # nested_dict = get_nested_dict_from_shot(h5_path)
        # self.sequence = nested_dict['sequence']
        # self.sequence_index = nested_dict['sequence_index']
        # self.labscript = nested_dict['labscript']
        # self.run_time = nested_dict['run time']
        # self.run_number = nested_dict['run number']
        # self.run_repeat = nested_dict['run repeat']

        # To speed up initialization we've copied over the relevant parts from
        # get_nested_dict_from_shot(). This isn't ideal since if the lyse code
        # is updated, then we'll need to update this as well. If necessary we
        # can revert back to the commented-out code above that actually calls
        # get_nested_dict_from_shot(), though things will take longer to run.
        root_attributes = self.get_attrs('/')

        # sequence
        seq_id = _ensure_str(root_attributes['sequence_id'])
        self.sequence = asdatetime(seq_id.split('_')[0])
        # sequence_index.
        try:
            self.sequence_index = root_attributes['sequence_index']
        except KeyError:
            self.sequence_index = None
        # labscript.
        self.labscript = _ensure_str(root_attributes['script_basename'])
        # run_time.
        try:
            self.run_time = self.sequence.value # self.sequence._time_repr gives HH:MM:SS format
        except KeyError:
            self.run_time = float('nan')
        # run_number.
        try:
            self.run_number = root_attributes['run number']
        except KeyError:
            self.run_number = float('nan')
        # run_repeat.
        try:
            self.run_repeat = root_attributes['run repeat']
        except KeyError:
            self.run_repeat = 0
        # If any other attributes are added here, make sure to edit
        # RepeatedShot.__init__() to transfer them to the RepeatedShot instance.

    def __getattr__(self, name):
        """Access a property of an instance that isn't defined.

        This method is called if code tries to access a property of an instance
        that isn't defined. This is likely an attempt to access a global's
        value or the result of a calculation which isn't in memory. That may be
        because the calculation hasn't been done yet, or it may be a result that
        isn't in memory but is stored in the shot's hdf5 file. We'll check the
        globals and the hdf5 file for the desired name and throw an error if it
        can't be found.

        This method implicitly assumes that the any saved result is saved in the
        group in the hdf5 file specified by self.group. It won't be able to find
        the result if it is saved in any other group. This is why the Shot class
        saves all of its results to the 'shot_results' group by default
        regardless of what script created it, so a Shot instance created in one
        script for some shot of the machine can find the results from any other
        Shot instance for created by any other script for the same shot of the
        machine.

        Note that this function is called internally by Python; you don't call
        it directly.

        Args:
            name (str): The name of the attribute that is being accessed.

        Raises:
            AttributeError: If the attribute doesn't exist and isn't in the hdf5
                file.

        Returns:
            The value of the requested attribute.
        """
        # First we'll check if a global with this name exists. We'll do this
        # first since it doesn't require accessing the hard drive so it can be
        # fast.
        try:
            return self.globals[name]
        except KeyError:
            pass

        # Next let's check if a scalar result with this name exists.
        try:
            # This will raise Exception if the result isn't in the file.
            return self.get_result(self.group, name)
        except Exception:
            pass

        # If it wasn't a scalar, let's see if an array result exists.
        try:
            return self.get_result_array(self.group, name)
        except Exception:
            pass

        # At this point the result can't be found, so let's throw an error.
        error_message = (f"The property {name} has not been produced by any "
                         "calculation, you may need to call "
                         "self.process_image() or another function to calculate "
                         "that result.")
        raise AttributeError(error_message)

    def save_result(self, result_name, result_value, **kwargs):
        """Save a scalar to the hdf5 file and as an attribute of this instance.

        This function can be called to store results of calculations. It is a
        convenience function that automatically saves the result as an attribute
        of this instance (so it can be accessed as self.result_name) and to the
        hdf5 file using self.run.save_result() (which means that the result
        should be a scalar). To save an array, use the self.save_result_array()
        method.

        Args:
            result_name (str): The name to use to store the result. Note that
                this should be given as a string. To access the attribute of the
                instance with the "dot" object notation, a string shouldn't be
                used. For example, a result might be saved with result_name set
                to 'atom_number', then to access it one would use
                self.atom_number (note the presence/lack of quotes). If its
                necessary or more convenient to access it with a string, the
                function getattr() can be used, e.g.
                getattr(self, 'atom_number').
            result_value (int, float): The value to be stored as result_name.
                Note that this should be a scalar value; to save an array use
                the self.save_result_array() method.
            **kwargs: Additional keyword arguments are passed to lyse.Run's
                save_result() method.
        """
        setattr(self, result_name, result_value)
        super().save_result(result_name, result_value, **kwargs)

    def save_result_array(self, result_name, result_array, **kwargs):
        """Save an array to the hdf5 file and as an attribute of this instance.

        This function can be called to store results of calculations. It is a
        convenience function that automatically saves the result as an attribute
        of this instance (so it can be accessed as self.result_name) and to the
        hdf5 file using self.run.save_result_array() (which means that the
        result should be an array). To save a scalar, use the self.save_result()
        method.

        Args:
            result_name (str): The name to use to store the result. Note that
                this should be given as a string. To access the attribute of the
                instance with the "dot" object notation, a string shouldn't be
                used. For example, a result might be saved with result_name set
                to 'od_image', then to access it one would use self.od_image
                (note the presence/lack of quotes). If its necessary or more
                convenient to access it with a string, the function getattr()
                can be used, e.g. getattr(self, 'od_image').
            result_array (np.array): The value to be stored as result_name.
                Note that this should be an array of values; to save a single
                scalar, use the self.save_result() method.
            **kwargs: Additional keyword arguments are passed to lyse.Run's
                save_result_array() method.
        """
        setattr(self, result_name, result_array)
        super().save_result_array(result_name, result_array, **kwargs)

    def process_image(self, atoms_image, no_atoms_image, background_image=None, plot=True):
        """Here we take in a series of absorption images, process them, and perform gaussian fits. From the gaussian fits,
        we can get the OD + the atom # in the cloud. Finally, we can plot the fits + the processed image if plot is true

        Args:
            atoms_image (2d image): image of the atoms with imaging beam turned on
            no_atoms_image (2d image): the image beam is turned on, but the atoms have decayed out of the trap
            background_image (2d image, optional): the image beam is off and there are no atoms. Defaults to None.
            plot (bool, optional): whether or not to plot the results. Defaults to True.
        """

        # remove the background from the images, ensure that there are not negative numbers in the images
        if background_image is not None:
            atoms_image = np.clip(atoms_image - background_image, 0, np.inf)
            no_atoms_image = np.clip(no_atoms_image - background_image, 0, np.inf)

        # divide the two to get the ratios of intensities. Used in the OD calculation
        self.processed_image = atoms_image / no_atoms_image

        # clean up any values that had infinities after division
        inf_indices = np.isinf(self.processed_image)
        nan_indices = np.isnan(self.processed_image)
        remove_indices = np.logical_or(inf_indices, nan_indices)
        self.processed_image[remove_indices] = 0

        # ADD IN ARTIFICIAL DATA FOR PRESENTATION PURPOSES. 
        # DELETE OR COMMENT THIS OUT LATER
        image_x = 700
        image_y = 600
        width = 150
        amplitude = .5
        for i in range(4*width):
            for j in range(4*width):
                self.processed_image[image_y+j, image_x+i] -= amplitude * np.exp(-(2*width-i)**2/width**2 - (2*width-j)**2/width**2)

        # If we do not have image_roi saved in the routine_storage variable..
        if not hasattr(routine_storage, 'image_roi'):
            # ask the user for an image roi! The user can choose an new roi by pressing ` (the key under the escape key)
            cv2.namedWindow("Image",2)
            cv2.resizeWindow("Image", 800, 600) 
            routine_storage.image_roi = cv2.selectROI("Image", self.processed_image, showCrosshair=True)
            cv2.waitKey(1)
            cv2.destroyAllWindows()

        # Get the rectangle parameters that the user selected! Save those and the roi in the HDF file
        self.x0, self.y0, self.w, self.h = routine_storage.image_roi
        self.save_result("roi", routine_storage.image_roi)
        self.processed_image_roi = self.processed_image[int(self.x0):int(self.x0+self.w), int(self.y0):int(self.y0+self.h)]
        self.save_result_array("processed_image", self.processed_image)

        # Get crossections from the ROI to fit; save them
        horizontal_crossection = self.processed_image_roi.sum(axis=1)/self.processed_image_roi.shape[1]
        vertical_crossection = self.processed_image_roi.sum(axis=0)/self.processed_image_roi.shape[0]
        self.save_result_array("horizontal_crossection", horizontal_crossection)
        self.save_result_array("vertical_crossection", vertical_crossection)
        
        # get the parameters of a gaussian + offset that fit the cross section for both vertical and horizontal
        horizontal_fit_params = fit_gaussian_with_offset(horizontal_crossection, indices=np.arange(self.x0, self.x0+self.w))
        vertical_fit_params = fit_gaussian_with_offset(vertical_crossection, indices=np.arange(self.y0, self.y0+self.h))
        self.save_result_array("horizontal_fit_params", horizontal_fit_params)
        self.save_result_array("vertical_fit_params", vertical_fit_params)

        # the gaussian parameters (params[0] is the center position, params[3] is the offset)
        amplitude = (horizontal_fit_params[2] + vertical_fit_params[2])/2
        h_width = horizontal_fit_params[1]
        v_width = vertical_fit_params[1]

        # Integrate the OD using the gaussian fit parameters, which is then converted to atom number using constants defined at the top of the page. 
        # You can check that integrating the 2d gaussian gives this eqn.
        od = 2 * np.pi * np.abs(amplitude) * np.abs(h_width) * np.abs(v_width)
        atom_number = OD_TO_ATOM_NUMBER * od
        self.save_result("od", od)
        self.save_result("atom_number", atom_number)

        # if plot, plot
        if plot:
            self.plot_absorption_image()
        
    def plot_absorption_image(self):
        """Plot the results of the process_image function
        """

        # if we have already created a figure, skip this.
        # if we have *not* created a figure, create a new figure
        # the code is written this way so that we do not have to recreate a figure each time we process a new shot
        if not hasattr(routine_storage, 'fig'):
            routine_storage.fig = plt.figure(constrained_layout=True, figsize=DEFAULT_FIGURE_SIZE)
            routine_storage.gs = routine_storage.fig.add_gridspec(3, 3)

            # if the user pressed the '`' key, ask the user for a new ROI on the next shot
            def on_press(event, key_text='`'):
                if event.key == key_text and hasattr(routine_storage, 'image_roi'):
                    delattr(routine_storage, "image_roi")

            # add the above function to our plot
            routine_storage.fig.canvas.mpl_connect('key_press_event', on_press)

        # the image occupies grid spaces [0, 0], [0, 1], [1, 0], and [1, 1] in our 3x3 grid
        image_axis = routine_storage.fig.add_subplot(routine_storage.gs[0:2, 0:2])

        plot_img = image_axis.imshow(self.processed_image, cmap=plt.get_cmap('plasma'))
        routine_storage.fig.colorbar(plot_img, ax=image_axis)
            
        # Create a Rectangle patch that denotes the selected ROI 
        rect = patches.Rectangle((self.x0, self.y0), self.w, self.h, linewidth=1, edgecolor='w', facecolor='none')

        # Add the patch to the Axes
        image_axis.add_patch(rect)

        # create a new plot to show the crossection + the fit
        horizontal_axis = routine_storage.fig.add_subplot(routine_storage.gs[2, 0:2], sharex=image_axis)

        # the x-points are the width of the rectangle we selected as the ROI
        x_points = np.linspace(self.x0, self.x0+self.w, 1000)
        # plot the abs of the log of the cross section, which we fit in process_image()
        horizontal_data_plot = horizontal_axis.scatter(np.arange(self.x0, self.x0+self.w), abs(np.log(self.horizontal_crossection)), s=1, c='y')
        # plot the fit of the horizontal cross section
        horizontal_fit_plot = horizontal_axis.plot(x_points, gaussian_with_offset(x_points, *self.horizontal_fit_params), c='r')[0]

        # do the same as above, except for the vertical crossection
        vertical_axis = routine_storage.fig.add_subplot(routine_storage.gs[0:2, 2], sharey=image_axis)

        y_points = np.linspace(self.y0, self.y0+self.h, 1000)
        vertical_data_plot = vertical_axis.scatter(abs(np.log(self.vertical_crossection)), np.arange(self.y0, self.y0+self.h), s=1, c='y')
        vertical_fit_plot = vertical_axis.plot(gaussian_with_offset(y_points, *self.vertical_fit_params), y_points, c='r')[0]
        vertical_axis.invert_xaxis()

        # add in some text results for the plot
        text_axis = routine_storage.fig.add_subplot(routine_storage.gs[2, 2])
        text_axis.set_axis_off()

        text_axis.text(0, 0.375, "Atom Number: {:.3E}".format(self.atom_number))
        text_axis.text(0, 0.75, "OD: {:.3E}".format(self.od))

        print("Atom Number: {:.3E}".format(self.atom_number))
        print("OD: {:.3E}".format(self.od))


# Below are classes that Zak made, but that I haven't had to use yet. I'm keeping them in case they are useful in the future


# class RepeatedShot(Shot):
#     """A class for grouping together shots with identical values for globals.

#     This class is used to group together shots with identical values for globals
#     to make it convenient to keep track of them and aggregate their results to
#     find averages, variances, and so on. Note that this class makes no efforts
#     to ensure that the shots provided to it are actually repeated iterations of
#     the same shot; it is up to the user to ensure that this is the case.
#     Therefore, the best way to create a RepeatedShot instance is to initialize
#     an instance of the Dataset class and use the RepeatedShot instances that it
#     creates.

#     This class inherits from Shot, so it has the same attributes that the Shot
#     class has. For more information on them, see that class's documentation. In
#     addition to the inherited attributes, this class has the attributes listed
#     below.

#     Attributes:
#         shot_list (list of Shot): A list of the Shot instances provided during
#             initialization. The Shot instances are sorted by run time, so their
#             ordering may be different than in the provided list.
#         last_shot (Shot): The last Shot instance in self.shot_list.
#     """

#     def __init__(self, shot_list):
#         """Create a RepeatedShot instance.

#         The shot_list will be copied, then the copy will be sorted. That means
#         that the order of shots in self.shot_list may end up being different
#         than the order in the provided shot_list argument.

#         Args:
#             shot_list (list of Shot instances): A list of shot instances which
#                 represent shots of the machine with identical input parameters,
#                 in particular identical values for globals. Note that this
#                 method does NOT check that all the globals have the same value,
#                 it is up to the caller to ensure that this is the case.
#         """
#         # Ensure shot_list is sorted by 'run time', for repeatability.
#         def sort_key(shot):
#             return shot.get_attrs('/')['run time']
#         shot_list = sorted(shot_list, key=sort_key)
#         self.shot_list = shot_list

#         # Pick a shot whose hdf5 file will be used to store the results from
#         # calculations done by this class. We'll just use the last one in
#         # shot_list.
#         self.last_shot = shot_list[-1]
#         h5_path = self.last_shot.h5_path

#         # Record on all shots which one will be used to store the data for the
#         # RepeatedShot instance.
#         for shot in shot_list:
#             shot.save_result('repeatedshot_results_file', h5_path)

#         # Typically we'd call the parent class's __init__() method here, but it
#         # slows things down doing so re-reads in a lot of data from disk. To
#         # speed things up we'll instead just copy over the attributes from the
#         # last shot. We'll still call the grandparent class's (Run's) __init__()
#         # though since it does a few other important things.
#         # super().__init__(h5_path)  # This is a bit slow.
#         Run.__init__(self, h5_path)
#         self.globals = self.last_shot.globals
#         self.sequence = self.last_shot.sequence
#         self.sequence_index = self.last_shot.sequence_index
#         self.labscript = self.last_shot.labscript
#         self.run_time = self.last_shot.run_time
#         self.run_number = self.last_shot.run_number
#         self.run_repeat = self.last_shot.run_repeat

#         # Make 'repeatedshot_results' in that file the default hdf5 group for
#         # saving results.
#         self.set_group('repeatedshot_results')

#     def get_image(self, *args):
#         """The average image of all of this RepeatedShot's Shot instances.

#         This method calls shot.get_image() on all of the images in
#         self.shot_list then returns the average of all of those images. The
#         arguments passed to this method are passed directly on to
#         shot.get_image(), which in turn call lyse.Run.get_image(), so the
#         calling syntax and required arguments are the same. For example you
#         could call self.get_image('camera', 'absorption', 'atoms').

#         Args:
#             orientation (str): The orientation of the camera from which the
#                 image was taken. This is included in labscript mainly for labs
#                 that have multiple cameras at different angles. As of this
#                 writing we should set this to 'camera' for our lab.
#             label (str): The 'name' argument passed during the call to
#                 camera.expose() in the labscript for the sequence. As of this
#                 writing we only use absorption imaging and we always set this to
#                 'absorption'
#             image (str): The 'frametype' argument passed during the call to
#                 camera.expose() in the labscript for the sequence. As of this
#                 writing the values we use for this are 'atoms', 'beam, and
#                 'background'.
#         """
#         # Initialize the array with the correct shape. Use double precision
#         # floats right away instead of 16 bit integers (the type returned by
#         # shot.get_image) to avoid integer overflow.
#         example_image = self.shot_list[0].get_image(*args)
#         average = np.zeros_like(example_image, dtype=np.double)
#         for shot in self.shot_list:
#             average += shot.get_image(*args)
#         average = average / self.n_shots
#         return average

#     def average_od_image(self):
#         """Average the od_image of all of the shots in self.shot_list.

#         This method averages all of the od_images from all of the shots in
#         self.shot_list and saves the result, both to the hdf5 file and as
#         self.od_image.

#         This method is automatically called by self.process_image(). However,
#         if can be useful to call it directly, for example if
#         shot.process_image() has been called on all of the shots in
#         self.shot_list (likely by Lyse), but repeatedshot.process_image()
#         hasn't been called. In that case calling repeatedshot.process_image()
#         would in turn call shot.process_image() on all of the shots, so that
#         analysis would be repeated. Instead you can call self.average_od_image()
#         directly, then the existing results from shot.process_image() will be
#         used.
#         """
#         # Initialize the array with the correct shape and data type.
#         od_image = np.zeros_like(self.shot_list[0].od_image)
#         for shot in self.shot_list:
#             od_image += shot.od_image

#         # Divide by self.n_shots to get the average.
#         od_image /= self.n_shots

#         # Save the results.
#         self.save_result_array('od_image', od_image)

#     def _calculate_od_image(self, absorption_image_processor):
#         # Process each shot's image and keep it in RAM until we're done with
#         # it.
#         for shot in self.shot_list:
#             shot.process_image(
#                 absorption_image_processor,
#                 free_image_ram=False,
#             )

#         # Average the results.
#         self.average_od_image()

#         # Delete each shot's od_image from memory to reduce RAM usage.
#         for shot in self.shot_list:
#             shot.free_image_ram()

#     def _integrate_od(self):
#         # Collect results from individual shots.
#         peak_od_list = []
#         integrated_od_list = []
#         atom_number_list = []
#         for shot in self.shot_list:
#             peak_od_list.append(shot.peak_od)
#             integrated_od_list.append(shot.integrated_od)
#             atom_number_list.append(shot.atom_number)

#         # Use the average the OD image before taking the peak OD to reduce the
#         # effects of noise. We'll approximate the uncertainty in peak OD using
#         # the variance of peak OD in individual images though.
#         peak_od = np.max(self.od_image)

#         # Set other values equal to the mean of the individual shot results.
#         integrated_od = np.mean(integrated_od_list)
#         atom_number = np.mean(atom_number_list)

#         # Calculate uncertainties, setting them to nan if we don't have enough
#         # data points.
#         if self.n_shots > 1:
#             std_factor = np.sqrt(self.n_shots - 1)
#             peak_od_uncertainty = np.std(peak_od_list) / std_factor
#             integrated_od_uncertainty = np.std(integrated_od_list) / std_factor
#             atom_number_uncertainty = np.std(atom_number_list) / std_factor
#         else:
#             peak_od_uncertainty = np.nan
#             integrated_od_uncertainty = np.nan
#             atom_number_uncertainty = np.nan

#         # Save the results.
#         self.save_result('peak_od', peak_od)
#         self.save_result('peak_od_uncertainty', peak_od_uncertainty)
#         self.save_result('integrated_od', integrated_od)
#         self.save_result('integrated_od_uncertainty', integrated_od_uncertainty)
#         self.save_result('atom_number', atom_number)
#         self.save_result('atom_number_uncertainty', atom_number_uncertainty)

#     @property
#     def n_shots(self):
#         """The number of shots in this RepeatedShot instance."""
#         return len(self.shot_list)


# class Dataset(Run):
#     """A class for aggregating data from different RepeatedShots.

#     Dataset inherits from lyse.Run so that it has the same hdf5 access methods.

#     Attributes:
#         seperate_sequences (bool): The value passed for separate_sequences
#             during initialization. This sets whether shots that have the same
#             values for all of their globals, but different values in the
#             'sequence' column in the Lyse dataframe (meaning they came from
#             different clicks of 'Engage' in runmanager) are grouped together
#             into the same RepeatedShot instances or put into separate
#             RepeatedShot instances. This should not be changed after
#             intialization.
#         repeatedshot_list (list of RepeatedShot instances): The list of
#             RepeatedShot instances created while grouping together the Shot
#             instances provided during initialization.
#         shot_list (list of Shot instances): A list of all of the Shot instances
#             from all of the RepeatedShot instances in self.repeatedshot_list.
#         last_shot (Shot): The last Shot instance in the shot_list of the last
#             RepeatedShot instance in self.repeatedshot_list. Some data is taken
#             from this Shot instance and is assumed to be representative of all
#             of the shots in the dataset. For example, it is assumed that all of
#             the shots have the same set of globals (although different values
#             for those globals), and that list of globals is taken from
#             self.last_shot.
#         globals_list (list of str): The list of globals, taken from
#             self.last_shot.
#         grouping_list (list of str): The list of attributes used to determine if
#             Shot instances should belong to the same or different RepeatedShot
#             instances. In practice this is essentially the same as
#             self.globals_list, except that 'sequence' will be prepended to the
#             list if separate_sequences was set to True.
#         h5_path (str): The path (including file name and extension) to the hdf5
#             file used to save any results from the Dataset instance, with the
#             default group set to 'dataset_results'. As of this writing, this is
#             set to self.last_shot.h5_path, but no data is saved by any of
#             Dataset's methods. Although if the user calls any of the methods
#             inherited from lyse.Run for writing to or reading from the hdf5
#             file, this is where the results will go or come from. In the future
#             it may be worthwhile to create a new hdf5 file for Dataset
#             instances, separate from the one for any shot, although that remains
#             to be seen.
#     """

#     def __init__(self, shot_list, separate_sequences=True):
#         """Initialize a Dataset instance.

#         Args:
#             shot_list (list of Shot instances or pandas.core.frame.DataFrame):
#                 A list of instances of the Shot class which should be included
#                 in the Dataset instance. Alternatively a pandas dataframe as
#                 returned by lyse.data() or
#                 multishot_utils.get_dataframe_subset() can be provided, in which
#                 case all entries in the dataframe will be included..
#             separate_sequences (bool, optional): (Default=True) Sets whether
#                 shots with different values of 'sequence' (i.e. shots from
#                 different clicks of 'Engage' in runmanager) but identical values
#                 for globals are grouped together into one RepeatedShot instance,
#                 or kept separate. Note that 'sequence' here refers to the value
#                 in the Lyse dataframe, which is not related to the name of the
#                 sequence's labscript file.
#         """
#         # If shot_list is a dataframe, convert it to a list of Shot instances.
#         if type(shot_list).__name__ == 'DataFrame':
#             # Make a list of all of the shots in the dataframe.
#             new_shot_list = []
#             for filepath in shot_list['filepath'].values:
#                 new_shot_list.append(Shot(filepath))
#             shot_list = new_shot_list

#         # Group the shots by their values for the globals.
#         self.separate_sequences = separate_sequences
#         grouped_shot_list = self._group_shots(shot_list, separate_sequences)
#         # Combine into RepeatedShot instances.
#         repeatedshot_list = []
#         for shot_group in grouped_shot_list:
#             # shot_group is a list of Shot instances which should all be in one
#             # RepeatedShot instance.
#             repeatedshot_list.append(RepeatedShot(shot_group))

#         # Sort the repeatedshot_list for repeatability. Sort by values of
#         # of attributes in self.grouping_list. The globals are listed in
#         # alphabetical order (except 'sequence' is in front if present). Numpy
#         # arrays mess up sorting so we'll convert them to tuples.
#         def sort_key(repeatedshot):
#             values = [getattr(repeatedshot, attribute)
#                       for attribute in self.grouping_list]
#             # Numpy arrays mess up sorting so we'll convert them to tuples.
#             sortable_values = []
#             for value in values:
#                 if isinstance(value, np.ndarray):
#                     sortable_values.append(tuple(value))
#                 else:
#                     sortable_values.append(value)
#             return sortable_values
#         repeatedshot_list = sorted(repeatedshot_list, key=sort_key)
#         self.repeatedshot_list = repeatedshot_list

#         # Keep track of the last shot as we'll use it for some things. Note that
#         # this is the last shot after sorting by values of globals, so it won't
#         # necessarily be the last shot chronologically or last shot in the
#         # provided shot_list.
#         last_shot = repeatedshot_list[-1].shot_list[-1]
#         self.last_shot = last_shot

#         # Use the hdf5 file of the last_shot of the last repeatedshot to store
#         # data. Note that RepeatedShot.__init__() sorts its shot instances for
#         # us.
#         # TODO: Ditch saving stuff from Dataset to the hdf5 file? Then shouldn't
#         # inherit from lyse.Run. Still would save results from each RepeatedShot
#         # and/or Shot to their corresponding hdf5 files.
#         h5_path = last_shot.h5_path

#         # Make 'dataset_results' in that file the default hdf5 group for saving
#         # results.
#         super().__init__(h5_path)
#         self.set_group('dataset_results')

#     def _group_shots(self, shot_list, separate_sequences):
#         # Get a list of all of the globals. We'll get it from the last shot.
#         shot = shot_list[-1]
#         globals_list = sorted(shot.globals.keys())
#         # Ignore shot_repetition_index.
#         globals_list.remove('shot_repetition_index')
#         self.globals_list = globals_list

#         # Also separate shots from different sequences if instructed to do so.
#         grouping_list = globals_list
#         if separate_sequences:
#             grouping_list = ['sequence'] + grouping_list
#         self.grouping_list = grouping_list

#         # Group the shots by the values for attributes in grouping_list.
#         grouped_shot_list = group_by_attributes(shot_list, grouping_list)
#         return grouped_shot_list

#     @property
#     def shot_list(self):
#         """List of all Shots in all RepeatedShots in self.repeatedshot_list."""
#         shot_list = [
#             shot for repeatedshot in self.repeatedshot_list
#             for shot in repeatedshot.shot_list
#         ]
#         return shot_list

#     def get_independent_globals(self):
#         """Get a list of the independent globals that were scanned.

#         This is mainly a convenience method that simply calls get_independents()
#         on self.last_shot, so it is assumed that the data in that shot's hdf5
#         file is representative of all of the shots in this Dataset instance. In
#         addition, if self.separate_sequences is True, then it checks if there
#         are multiple values for 'sequence' in self.repeatedshot_list and adds it
#         to the list of independents if there were.

#         For more information, see get_independents().

#         Returns:
#         independents (list of strings): A list of strings, each of which
#             specifies a global that was scanned. Only one parameter per
#             dimension of the scan is returned. When two parameters are scanned
#             in parallel, only one of them will be returned here. Additionally,
#             'sequence' is included in this list if self.separate_sequences is
#             True and there are multiple values for 'sequence' in
#             self.repeatedshot_list. The list will be sorted alphabetically.
#         """
#         # TODO: Get independents just by seeing what globals vary and keeping
#         # any of them that aren't dependent variables in
#         # the dict from self.last_shot.get_globals_expansion()? Would be helpful
#         # if things are scanned by hand. However doing that would make it
#         # annoying to set n_sequences_to_analyse correctly, so maybe it isn't
#         # worth the hassle.
#         independents = get_independents(self.last_shot)

#         # If separate_sequences is True and there are multiple values for
#         # 'sequence', then include it in the list of independents. Only iterate
#         # if self.repeatedshot_list isn't empty.
#         if self.separate_sequences and self.repeatedshot_list:
#             all_same = True
#             repeatedshot_list = self.repeatedshot_list
#             n_repeatedshots = len(repeatedshot_list)
#             first_sequence = repeatedshot_list[0].sequence
#             j = 1
#             while all_same and j < n_repeatedshots:
#                 if repeatedshot_list[j].sequence != first_sequence:
#                     all_same = False
#                 j += 1
#             if not all_same:
#                 independents = ['sequence'] + independents

#         # Ensure that the list is sorted.
#         independents.sort()

#         return independents

#     def get_dependent_globals(self):
#         """Get a list of the dependent globals that were scanned.

#         This is mainly a convenience method that simply calls get_dependents()
#         on self.last_shot, so it is assumed that the data in that shot's hdf5
#         file is representative of all of the shots in this Dataset instance.

#         For more information, see get_dependents().

#         Returns:
#             dependents (list of strings): A list of strings, each of which
#                 specifies a global that was scanned. This list includes are the
#                 globals that were scanned but are not in the list of
#                 independents returned by get_independents() (with the exception
#                 of shot_repetition_index, which does not appear in either list).
#                 The list will be sorted alphabetically.
#         """
#         dependents = sorted(get_dependents(self.last_shot))
#         return dependents

#     def get_beam_image_file_name_patterns(self):
#         """Get a list of suggested file name patterns for beam images.

#         This method is mainly designed to be used in tandem with the
#         initialize_from_file_patterns() method of the AbsorptionImageProcessor
#         class. It generates a list of strings giving paths with wildcards to
#         match the names of shot files that could be used to perform PCA
#         absorption imaging analysis. The paths are built assuming that data is
#         stored in the default Labscript pattern, namely that the path looks like
#         r"base_path/sequence_name/year/month/day/sequence_index/file_name.h5".
#         Care is taken to make this platform independent though, so it should
#         still work if using forward or backward slashes, etc.

#         The paths are generated by looking at the paths to all of the shots in
#         the dataset and getting a list of all of the distinct paths. Then for
#         each of those paths, the sequence_name, sequence_index, and file_name
#         are replaced with the "*" wildcard so that the pattern will match shots
#         with any value for those parts of the path.

#         Returns:
#             beam_image_file_name_patterns (list of strings): A list of strings,
#                 each specifying a path with "*" wildcards for matching hdf5 shot
#                 files that could be used for absorption image processing of the
#                 data in this Dataset instance.
#         """
#         # Get list of directories that have data.
#         file_paths = [shot.h5_path for shot in self.shot_list]
#         directories = [os.path.split(file_path)[0] for file_path in file_paths]

#         # Get set of unique directories (i.e. remove duplicates).
#         directories = set(directories)

#         # Construct the file name pattern for each directory.
#         beam_image_file_name_patterns = []
#         for directory in directories:
#             # Break path into a list of folder names.
#             directory = os.path.normpath(directory)
#             path_folder_list = directory.split(os.sep)
#             # Path is assumed to look like
#             # r"base_path\sequence_name\year\month\day\sequence_index".

#             # Extract the base path.
#             base_path = path_folder_list[:-5]
#             base_path = os.path.join(*base_path)

#             # Extract date folders path.
#             date_path = path_folder_list[-4:-1]
#             date_path = os.path.join(*date_path)

#             # Combine with wildcards for sequence_name, sequence_index, and file
#             # name.
#             beam_image_file_name_pattern = os.path.join(
#                 base_path,  # Path to where data is stored.
#                 "*",  # Match any sequence.
#                 date_path,  # Only use images from same date as shots.
#                 "*",  # Match any sequence index.
#                 "*.h5",  # Match all hdf5 files.
#             )
#             beam_image_file_name_patterns.append(beam_image_file_name_pattern)

#         # Remove duplicates again, since we may have duplicates after replacing
#         # some parts with "*".
#         beam_image_file_name_patterns = list(set(beam_image_file_name_patterns))

#         return beam_image_file_name_patterns

#     def process_images(self, absorption_image_processor):
#         """Call repeatedshot.process_image() on each repeatedshot.

#         This is a convenience method that iterates over the instances of the
#         RepeatedShot class in self.repeatedshot_list and calls their
#         process_image() method with the given absorption_image_processor.

#         See the documentation for RepeatedShot.process_image() for more
#         information.

#         Args:
#             absorption_image_processor (AbsorptionImageProcessor): An instance
#                 of the AbsorptionImageProcessor class from
#                 pythonlib.RbLab.AbsorptionImageProcessor, configured as desired
#                 (e.g. with reference beam images already added, the atom region
#                 mask configured, etc.).
#         """
#         for repeatedshot in self.repeatedshot_list:
#             repeatedshot.process_image(absorption_image_processor)

#     def average_od_images(self):
#         """Call repeatedshot.average_od_image() on each repeatedshot.

#         This is a convenience method that iterates over the instances of the
#         RepeatedShot class in self.repeatedshot_list and calls their
#         average_od_image() method.

#         See the documentation for RepeatedShot.average_od_image() for more
#         information.
#         """
#         for repeatedshot in self.repeatedshot_list:
#             repeatedshot.average_od_image()

#     def integrate_od_images(self):
#         """Call repeatedshot.integrate_od_image() on each repeatedshot.

#         This is a convenience method that iterates over the instances of the
#         RepeatedShot class in self.repeatedshot_list and calls their
#         integrate_od_image() method.

#         See the documentation for RepeatedShot.integrate_od_image() for more
#         information.
#         """
#         for repeatedshot in self.repeatedshot_list:
#             repeatedshot.integrate_od_image()

#     def fit_gaussians(self):
#         """Call repeatedshot.process_image() on each repeatedshot.

#         This is a convenience method that iterates over the instances of the
#         RepeatedShot class in self.repeatedshot_list and calls their
#         fit_gaussians() method.

#         See the documentation for RepeatedShot.fit_gaussians() for more
#         information.
#         """
#         for repeatedshot in self.repeatedshot_list:
#             repeatedshot.fit_gaussians()

#     def group_repeatedshots(self, attributes_list, data_constraints=()):
#         """Group repeatedshots by their values for attributes in attributes_list.

#         This method is used to group together the RepeatedShot instances in
#         self.repeatedshot_list. This is useful for determining which points in a
#         plot should be joined with a line, and which should lie on distinct
#         lines.

#         Note that this is different from self._group_shots(). That method
#         figures out which individual shots have matching values for all of their
#         globals and is used to figure out how to group the individual shots into
#         RepeatedShot instances. This method then takes those RepeatedShot
#         instances and groups them into lists based on only the attributes
#         (usually globals) provided in the attributes_list argument to this
#         function. In particular this method returns a list of lists of
#         RepeatedShot instances, while self._group_shots() returns a list of list
#         of Shot instances. It may be useful for the user to call this
#         self.group_repeatedshots() directly but they probably won't ever need to
#         call self._group_shots() directly.

#         Args:
#             attributes_list (list of str): The names of the attributes whose
#                 values should be the same between two RepeatedShot instances in
#                 order for those two instances to be put into the same group.
#             data_constraints (list of constraints): (Default=()) This argument
#                 is passed on to self.get_filtered_repeatedshot_list() and can be
#                 used to constrain which RepeatedShot instances are included in
#                 the returned lists. See that method's documentation for more
#                 information.

#         Returns:
#             grouped_repeatedshot_list (list of lists of RepeatedShot): A list of
#                 lists. Each sublist is a list of RepeatedShot instances which
#                 have the same values for all of the attributes listed in
#                 attributes_list.
#         """
#         # Get a list of repeatedshot instances that satisfy the contstraints.
#         repeatedshot_list = self.get_filtered_repeatedshot_list(
#             data_constraints)

#         # Group the repeated shots by the values for attributes in
#         # attributes_list.
#         grouped_repeatedshot_list = group_by_attributes(
#             repeatedshot_list, attributes_list)
#         return grouped_repeatedshot_list

#     def get_filtered_repeatedshot_list(
#             self, data_constraints, repeatedshot_list=None):
#         """Get a subset of self.repeatedshot_list that satisfy data_constraints.

#         To avoid issues with finite numerical precision, this method uses
#         isclose() from the python standard math library to compare values. This
#         means that floats are said to be equal if they are the same to within
#         about 1 part in 10^9, which is the default relative tolerance of
#         isclose(). The absolute tolerance is left at its default value of zero.

#         Args:
#             data_constraints (list of tuples): A list of constraints which
#                 RepeatedShot instances must satisfy in order to be included in
#                 the returned list. Each constraint should be a tuple. The first
#                 element should be the name of an attribute that the
#                 RepeatedShot instances have. The second and third elements of
#                 the tuple should be the minimum and maximum values (inclusively)
#                 that entries in the returned list should have. If the third
#                 entry in the tuple is omitted, then only RepeatedShot instances
#                 with the given attribute approximately equal (judged by
#                 isclose()) to the second element of the tuple will be returned.
#                 For example, ('atom_number', 1e3, 100e3) would return a list of
#                 RepeatedShot instances with atom number between 1e3 and 100e3,
#                 and ('sideband_cool_z_coil', 1.0) would return a list of
#                 RepeatedShot instances that have sideband_cool_z_coil equal to
#                 one within a precision of about nine decimal digits. It is also
#                 acceptable to use the two-element form for attributes that have
#                 non-numerical values, in which case only RepeatedShot instances
#                 which have the speicified value will be returned. For example,
#                 ('description', 'Fast Cooling') would return a list of
#                 RepeatedShot instances for which repeatedshot.description was
#                 set to 'Fast Cooling'.
#             repeatedshot_list (list of RepeatedShot instances, optional):
#                 (Default=None) A list of RepeatedShot instances from which the
#                 entries in the returned list will be drawn. If set to None, then
#                 self.repeatedshot_list will be used.

#         Returns:
#             repeatedshot_list (list of RepeatedShot instances): A subset of the
#                 input repeatedshot_list which containts only RepeatedShot
#                 instances that satisfy all of the constraints in
#                 data_constraints.
#         """
#         # Start with all of the repeatedshots if no list is provided.
#         if repeatedshot_list is None:
#             repeatedshot_list = self.repeatedshot_list

#         # Get a copy of repeatedshot_list to avoid editing the original.
#         repeatedshot_list = repeatedshot_list.copy()

#         # Iterate over constraints, popping out RepeatedShot instances that do
#         # not satisfy them.
#         for constraint in data_constraints:
#             attribute = constraint[0]
#             if len(constraint) == 2:
#                 # In this case ensure that the attribute's value is equal to the
#                 # requested value, at least to within a given precision for
#                 # numerical values.
#                 requested_value = constraint[1]
#                 keep_list = []
#                 for repeatedshot in repeatedshot_list:
#                     actual_value = getattr(repeatedshot, attribute)
#                     if actual_value == requested_value:
#                         keep_list.append(repeatedshot)
#                     else:
#                         # See if values are close, catching TypeError thrown if
#                         # one or more of the values is not a number.
#                         try:
#                             if isclose(actual_value, requested_value):
#                                 keep_list.append(repeatedshot)
#                         except TypeError:
#                             pass
#                 repeatedshot_list = keep_list
#             elif len(constraint) == 3:
#                 # In this case ensure that the attribute's value is greater than
#                 # the first provided value and less than the second provided
#                 # value, or approximately equal to one of the end values.
#                 minimum_value = constraint[1]
#                 maximum_value = constraint[2]
#                 keep_list = []
#                 for repeatedshot in repeatedshot_list:
#                     actual_value = getattr(repeatedshot, attribute)

#                     # Check if high enough.
#                     is_greater = (actual_value > minimum_value)
#                     is_equal = isclose(actual_value, minimum_value)
#                     high_enough = (is_greater or is_equal)

#                     # Check if low enough.
#                     is_less = (actual_value < maximum_value)
#                     is_equal = isclose(actual_value, maximum_value)
#                     low_enough = (is_less or is_equal)

#                     # Keep if both constraints are satisfied.
#                     if high_enough and low_enough:
#                         keep_list.append(repeatedshot)
#                 repeatedshot_list = keep_list

#         # Now the repeatedshot_list should only have RepeatedShot instances that
#         # satisfy all of the constraints, so we can return it.
#         return repeatedshot_list

#     def get_repeatedshot_values(self, attribute_list, data_constraints=()):
#         """Get a list of lists of values of the specified attributes.

#         This method retrieves the values of each attribute in attribute_list for
#         each RepeatedShot instance in self.repeatedshot_list that satisfies the
#         constraints in data_constraints. The results are returned as a list of
#         lists, one sublist for each attribute in attribute list. This allows
#         unpacking values nicely as in the following example:
#         `x_values, y_values = dataset.get_repeatedshot_values([x_attribute, y_attribute])`

#         This method always returns a list of lists, even when there is only one
#         entry in attribute_list. The only exception is if attribute_list is
#         empty, then a single empty list is returned.

#         Args:
#             attribute_list (list of str): A list of strings, each of which
#                 should specify an attribute that the RepeatedShot instances in
#                 self.repeatedshot_list that would be accessible through python's
#                 "dot" notation. Note that this should be passed as a list, even
#                 if only one attribute is requested.
#             data_constraints (list of constraints): (Default=()) This argument
#                 is passed on to self.get_filtered_repeatedshot_list() and can be
#                 used to constrain which RepeatedShot instances are included in
#                 the returned lists. See that method's documentation for more
#                 information.

#         Returns:
#             values_lists (list of lists): The values of all the attributes in
#                 attribute_list for the RepeatedShot instances. Each sublist
#                 containts all of the the values of one attribute for all of the
#                 included RepeatedShot instances.
#         """
#         # Get a list of repeatedshot instances that satisfy the contstraints.
#         repeatedshot_list = self.get_filtered_repeatedshot_list(
#             data_constraints)

#         # Iterate over requested attributes.
#         values_lists = []
#         for attribute in attribute_list:
#             # Get a list of values for this attribute.
#             values_list = [getattr(repeatedshot, attribute)
#                            for repeatedshot in repeatedshot_list]
#             # Add this to the list of similar lists.
#             values_lists.append(values_list)

#         # Return the result.
#         return values_lists

#     def map_function(self, function, data_constraints=()):
#         """Apply a function to elements in self.repeatedshot_list.

#         This can be used both for functions that return results, and for
#         functions which simply modify the attributes of the RepeatedShot
#         instances.

#         Args:
#             function (function): The function that should be applied to each
#                 element of self.repeatedshot_list.
#             data_constraints (list of constraints): (Default=()) This argument
#                 is passed on to self.get_filtered_repeatedshot_list() and can be
#                 used to constrain which RepeatedShot instances have fucntion
#                 applied to them. See the documentation for
#                 self.get_filtered_repeatedshot_list() for more information.

#         Returns:
#             results (list): A list containing the values returned from each call
#                 of function. If nothing is returned by function, this will be a
#                 list of None.
#             repeatedshot_list (list of RepeatedShot instances): A list of the
#                 RepeatedShot instances to which function was applied. This may
#                 not include all of the elements in self.repeatedshot_list due to
#                 filtering from data_constraints.
#         """
#         repeatedshot_list = self.get_filtered_repeatedshot_list(
#             data_constraints)
#         results = []
#         for repeatedshot in repeatedshot_list:
#             results.append(function(repeatedshot))
#         return results, repeatedshot_list

#     def plot_lines(self, x_attribute, y_attribute, axes=None,
#                    x_error_attribute=None, y_error_attribute=None,
#                    ignore_globals=None, data_constraints=(), order_by=None,
#                    generate_legend=True, label_by=None, errorbar_args={},
#                    plot_grid=True, grid_args={}, plot_minor_grid=True):
#         """Plot data as one or more lines.

#         This method plots the value for y_attribute as a function of x_attribute
#         for all of the entries in self.repeatedshot_list which satisfy the
#         constraints specified in data_constraints.

#         A separate line is plotted for each combination of all varied globals
#         (and 'sequence' value is self.separate_sequences is True). This
#         effectively lets us plot higher dimensional data in a 2D plot. The
#         values of globals in ignore_globals are ignored when determining which
#         RepeatedShot instances belong to the same line, so it can be used to
#         coerce RepeatedShot instances into the same line if desired.

#         Args:
#             x_attribute (str): The name of the attribute that should be used for
#                 the x-axis of the plot. This should be an attribute that the
#                 entries in self.repeatedshot_list have.
#             y_attribute (str): The name of the attribute that should be used for
#                 the y-axis of the plot. This should be an attribute that the
#                 entries in self.repeatedshot_list have.
#             axes (matplotlib.axes._subplots.AxesSubplot, optional):
#                 (Default=None) The axes on which the data should be plotted. If
#                 set to None, new axes on a new figure will be used.
#             x_error_attribute (str, optional): (Default=None) The name of the
#                 attribute that should be used for the error bars in the
#                 x-direction. This should be an attribute that the entries in
#                 self.repeatedshot_list have. If set to None, no error bars will
#                 be plotted.
#             y_error_attribute (str, optional): (Default=None) The name of the
#                 attribute that should be used for the error bars in the
#                 y-direction. This should be an attribute that the entries in
#                 self.repeatedshot_list have. If set to None, no error bars will
#                 be plotted.
#             ignore_globals (list of str, optional): (Default=None) The values
#                 of attributes in ignore_globals will be ignored when determining
#                 which RepeatedShot instances belong to the same line. If set to
#                 the default value of None, then only the globals in
#                 self.get_dependent_globals() will be ignored. If other globals
#                 are provided (instead of passing None), it is recommended to add
#                 the globals in self.get_dependent_globals() to that list.
#             data_constraints (list of constraints): (Default=()) This argument
#                 is passed on to self.get_filtered_repeatedshot_list() and can be
#                 used to constrain which RepeatedShot instances are included in
#                 the returned lists. See that method's documentation for more
#                 information.
#             order_by (str, optional): (Default=None) The name of an attribute
#                 that should be used to order the RepeatedShot instances within
#                 each line. This determines which points are joined via line
#                 segments. If set to None, then it will be set to x_attribute so
#                 that the line runs continuously left to right without ever
#                 doubling back on itself. Setting it to something other than None
#                 is useful for doing things like parametric plots where the
#                 ordering of points should be determined by some parameter other
#                 than the x-axis variable.
#             generate_legend (bool, optional): (Default=True) Sets whether or not
#                 a legend is included with the axes. The labels are generated
#                 from the values of the attributes in label_by, which defaults to
#                 use self.get_independent_globals(), except for the attributes
#                 that define the axes.  The labels for the legends are generated
#                 automatically whether generate_legend is True or False, so a
#                 legend may still be created manually after this method returns,
#                 if desired. Note that if there are no additional independently
#                 scanned globals, there will be nothing to put in the legend and
#                 so in that case it won't be generated even if generate_legend is
#                 set to True. If made, the legend will be placed outside of the
#                 plot to the right to avoid overlapping with the plot at all.
#             label_by (list of str, optional): (Default=None) The globals whose
#                 names are included in this list will have their names and values
#                 included in the legend, one entry for each line. If set to None,
#                 then the globals in self.get_independent_globals() will be used.
#                 If the names are specified manually, you may want to include the
#                 entries from self.get_independent_globals() as well. Note that
#                 to avoid misleading entries, if an entry in label_by is the
#                 attribute used as one of the axes in the plot, then it will be
#                 ignored. Keep in mind that only one label per line is added to
#                 the legend, so the globals included should have the same value
#                 for all points in the line so that the legend isn't misleading
#                 (no checks are done to ensure that this is the case).
#             errorbar_args (dict, optional): (Default={}) Keyword-style arguments
#                 can be passed to matplotlib's errorbar function (the one that is
#                 used for both the lines and the error bars) by including them in
#                 this dictionary. Note that the name of the arguments should be
#                 specifed as strings, so this can be something like
#                 {'barsabove ':True}. Some default options, e.g. markersize, are
#                 overwritten by this function, but user-provided values for those
#                 options will override the settings here.
#             plot_grid (bool, optional): (Default=True) Sets whether or not grid
#                 lines will be plotted.
#             grid_args (dict, optional): (Default={}) Keyword-style arguments can
#                 be passed to matplotlib's errorbar function by including them in
#                 this dictionary, similar to other optional argument
#                 errobar_args. Of course the value of grid_args has no effect if
#                 plot_grid is set to False. Similar to errorbars_dict, some
#                 default options to grid() are overwritten, but user-provided
#                 arguments take precedent over that.
#             plot_minor_grid (bool, optional): (Default=True) Sets whether or not
#                 grid lines are plotted for minor tick marks as well. If
#                 plot_grid is set to False then the minor grid will not be
#                 plotted and this argument will be ignored.

#         Returns:
#             axes (matplotlib.axes._subplots.AxesSubplot): The axes onto which
#                 the plot was made.
#         """
#         # Set up new axes if necessary.
#         if axes is None:
#             fig = plt.figure(figsize=_DEFAULT_FIGURE_SIZE)
#             axes = fig.add_subplot(111)

#         # Set ignore_globals to self.get_dependent_globals() if necessary.
#         if ignore_globals is None:
#             ignore_globals = self.get_dependent_globals()

#         # Set order_by to x_attribute if it was None.
#         if order_by is None:
#             order_by = x_attribute

#         # Set label_by to self.get_independent_globals() if necessary.
#         if label_by is None:
#             label_by = self.get_independent_globals()

#         # Copy errorbar_args to avoid editing the input.
#         errorbar_args = errorbar_args.copy()

#         # Set some nice default values for errorbar options, but don't overwrite
#         # user-provided errorbar_args.
#         default_errorbar_dict = {
#             'fmt': '-o',
#             'markersize': 4,
#             'capsize': 2,
#         }
#         # User input will override the settings here.
#         errorbar_args = {**default_errorbar_dict, **errorbar_args}

#         # Copy grid_args to avoid editing the input.
#         grid_args = grid_args.copy()

#         # Set some nice default values for grid options, but don't overwrite
#         # user-provided grid_args.
#         default_grid_args = {
#             'b': plot_grid,  # Turns grid on/off.
#             'which': 'both',
#             'color': 'black',
#         }
#         # User input will override the settings here.
#         grid_args = {**default_grid_args, **grid_args}

#         # Get list of all attributes to use for grouping RepeatedShot instances
#         # into lines. We'll make a copy to avoid editing the original (lists are
#         # mutable).
#         grouping_list = self.grouping_list.copy()

#         # Ensure x_attribute and y_attribute are not in the list. We'll catch
#         # the ValueError thrown if they aren't in the list.
#         try:
#             grouping_list.remove(x_attribute)
#         except ValueError:
#             pass
#         try:
#             grouping_list.remove(y_attribute)
#         except ValueError:
#             pass

#         # Remove the globals listed in ignore_globals. We won't stop the
#         # ValueError thrown if a global doesn't exist so that we don't ignore
#         # the user's input. Instead we'll just make it more informative.
#         for attribute in ignore_globals:
#             try:
#                 grouping_list.remove(attribute)
#             except ValueError:
#                 message = (f"Global '{attribute}' is in ignore_globals but not "
#                            "in self.grouping_list. Call this method with a "
#                            "corrected value for ignore_globals.")
#                 raise ValueError(message)

#         # Get a list of lists; one list for each line in the plot. Take only
#         # datapoints that meet the criteria given by data_constraints.
#         lines_list = self.group_repeatedshots(grouping_list, data_constraints)

#         # Don't include the x_attribute or y_attribute in legend label since
#         # they vary along a given line.
#         # Copy label_by to avoid editing the input.
#         label_by = list(label_by.copy())  # Ensure it's a list to use remove().
#         if x_attribute in label_by:
#             label_by.remove(x_attribute)
#         if y_attribute in label_by:
#             label_by.remove(y_attribute)

#         # Plot each of the lines.
#         for line in lines_list:
#             # Sort the data points by the parameter specified by order_by.
#             line.sort(key=lambda x: getattr(x, order_by))

#             # Get x and y values.
#             x_values = [getattr(repeatedshot, x_attribute)
#                         for repeatedshot in line]
#             y_values = [getattr(repeatedshot, y_attribute)
#                         for repeatedshot in line]

#             # Get errors if provided.
#             if x_error_attribute:
#                 x_error_values = [
#                     getattr(
#                         repeatedshot,
#                         x_error_attribute) for repeatedshot in line]
#             else:
#                 x_error_values = None
#             if y_error_attribute:
#                 y_error_values = [
#                     getattr(
#                         repeatedshot,
#                         y_error_attribute) for repeatedshot in line]
#             else:
#                 y_error_values = None

#             # Create a label for the legend.
#             repeatedshot = line[0]
#             label = [
#                 f"{attribute} = {getattr(repeatedshot, attribute)}" for attribute in label_by]
#             label = ', '.join(label)
#             # User input for label will overwrite the setting here.
#             kwargs = {'label': label, **errorbar_args}

#             # Add the line to the plot.
#             axes.errorbar(
#                 x_values,
#                 y_values,
#                 yerr=y_error_values,
#                 xerr=x_error_values,
#                 **kwargs
#             )

#         # Add the grid if instructed to do so. The 'b' argument in grid_args
#         # will determine whether or not the grid is shown.
#         axes.grid(**grid_args)

#         # Add minor grid if instructed to do so.
#         if plot_grid and plot_minor_grid:
#             axes.xaxis.set_minor_locator(AutoMinorLocator())
#             axes.yaxis.set_minor_locator(AutoMinorLocator())
#             # Make minor grid easily distinguishable from major grid.
#             axes.grid(which='minor', linestyle='--', color='gray')

#         # Set axes labels. Include units for attributes that are globals which
#         # have units (i.e. units isn't an empty string).
#         units = self.last_shot.get_units()
#         xlabel = x_attribute
#         if x_attribute in self.globals_list and units[x_attribute]:
#             xlabel = xlabel + f" ({units[x_attribute]})"
#         ylabel = y_attribute
#         if y_attribute in self.globals_list and units[y_attribute]:
#             ylabel = ylabel + f" ({units[y_attribute]})"
#         axes.set_xlabel(xlabel)
#         axes.set_ylabel(ylabel)

#         # Make name of labscript the title for the plot. Typically all of the
#         # shots will be from the same labscript, just with different values for
#         # globals, so we'll just take the name of the labscript from one shot.
#         axes.set_title(self.last_shot.labscript)

#         # Generate the legend. We'll put it off on the right side of the axes
#         # by default to avoid covering up data (the legend is often quite
#         # large). Only make the legend if label_by is nonempty.
#         if generate_legend and label_by:
#             axes.legend(loc='upper left', bbox_to_anchor=(1, 1))

#         # Return the axes on which the plot was made.
#         return axes

#     def plot_lines_atom_number(self, x_parameter, *args, **kwargs):
#         """Convenience method for plotting the atom number.

#         This method is a thin wrapper around self.plot_lines() which
#         automatically sets y_parameter and y_error_attribute for plotting the
#         atom number. Additionally, it changes the y-axis text to "Atom Number"
#         in place of "atom_number" to make things prettier.

#         Args:
#             x_parameter (str): The parameter to use for the x-axis. See
#                 self.plot_lines() for more information.
#             *args: Additional unnamed arguments are passed on to
#                 self.plot_lines().
#             **kwargs: Additional keyword argument are passed on to
#                 self.plot_lines().

#         Returns:
#             axes (matplotlib.axes._subplots.AxesSubplot): The axes on which the
#                 plot was made. See self.plot_lines() for more information.
#         """
#         axes = self.plot_lines(
#             x_parameter,
#             'atom_number',
#             y_error_attribute='atom_number_uncertainty',
#             *args,
#             **kwargs
#         )

#         # Label y-axis nicely.
#         axes.set_ylabel("Atom Number")
#         return axes

#     def plot_lines_temperature(self, x_parameter, direction='both', **kwargs):
#         """Convenience method for plotting the temperature.

#         This method is a thin wrapper around self.plot_lines() which
#         automatically sets y_parameter and y_error_attribute for plotting the
#         temperature. Additionally, it changes the y-axis text to be more
#         informative and readable.

#         The one nontrivial thing that this method does is overlay the vertical
#         and horizontal temperatures on the same axis if direction='both'.

#         Note: The keyword arguments linestyle and label will be ignored.

#         Args:
#             x_parameter (str): The parameter to use for the x-axis. See
#                 self.plot_lines() for more information.
#             direction (str): (Default='both') Sets which temperatures should be
#                 plotted. This should be set to 'horizontal', 'vertical', or
#                 'both'. If direction is set to anything else, a ValueError is
#                 raised.
#             **kwargs: Additional keyword argument are passed on to
#                 self.plot_lines().

#         Raises:
#             ValueError: If direction is anything other than 'horizontal',
#                 'vertical', or 'both', a ValueError is raised.

#         Returns:
#             axes (matplotlib.axes._subplots.AxesSubplot): The axes on which the
#                 plot was made. See self.plot_lines() for more information.
#         """
#         # Check direction input is valid.
#         if direction not in ['horizontal', 'vertical', 'both']:
#             error_message = ("direction must be 'horizontal', 'vertical', or "
#                              "'both'")
#             raise ValueError(error_message)

#         # Interpret direction input. Expressions in parentheses below evaluate
#         # to True or False.
#         plot_horizontal = (direction in ['horizontal', 'both'])
#         plot_vertical = (direction in ['vertical', 'both'])

#         # Copy kwargs to avoid editing the input.
#         kwargs = kwargs.copy()

#         # Ensure errorbar_args is in kwargs to make code below a bit simpler.
#         if not 'errorbar_args' in kwargs:
#             kwargs['errorbar_args'] = {}

#         # Remove keyword arguments that would cause trouble below if they are
#         # present in errorbar_args.
#         kwargs['errorbar_args'].pop('linestyle', None)
#         kwargs['errorbar_args'].pop('label', None)

#         # Plot the horizontal temperature if requested.
#         if plot_horizontal:
#             axes = self.plot_lines(
#                 x_parameter,
#                 'horizontal_temperature',
#                 # TODO: y_error_attribute='horizontal_temperature_uncertainty',
#                 **kwargs
#             )
#             # Reset color cycle so that corresponding horizontal temperatures
#             # lines and vertical temperature lines are the same color.
#             axes.set_prop_cycle(None)
#             # Ensure axes is in kwargs so that the vertical temperature is
#             # plotted on the same axes.
#             kwargs['axes'] = axes
#             # The labels for the legend have been made (we won't make duplicate
#             # entries for the vertical temperature lines) so make sure that no
#             # more are generated.
#             kwargs['errorbar_args']['label'] = None

#         # Plot the vertical temperature if requested.
#         if plot_vertical:
#             # Set linestyle to dashed to distinguish vertical from horizontal
#             # temperature.
#             kwargs['errorbar_args']['linestyle'] = '--'
#             axes = self.plot_lines(
#                 x_parameter,
#                 'vertical_temperature',
#                 # TODO: y_error_attribute='vertical_temperature_uncertainty',
#                 **kwargs
#             )

#         # Set a nice y-axis label.
#         if plot_horizontal and plot_vertical:
#             axes.set_ylabel("Temperature ($\\mu$K)\n"
#                             "Horizontal=Solid, Vertical=Dashed")
#         elif plot_horizontal:
#             axes.set_ylabel("Horizontal Temperature ($\\mu$K)")
#         elif plot_vertical:
#             axes.set_ylabel("Vertical Temperature ($\\mu$K)")

#         # Return the axes on which the plot was made.
#         return axes

#     def plot_colors(self, x_attribute, y_attribute, z_attribute, axes=None,
#                     data_constraints=(), plot_contours=True, contourf_args={},
#                     contour_args={}):
#         """Make a 2D color plot of data.

#         This method uses matplotlib's contourf (and optionally contour) plotting
#         function. Those methods require data to be on a rectangular grid, but
#         the values of x_attribute and y_attribute might not lie on a grid. To
#         work around this, x and y values are generated for a grid of points,
#         then the z values are generated via nearest-neighbor interpolation. This
#         probably isn't as efficient as doing something with Voronoi teslation
#         and it might be more prone to imaging artifacts, but it is more
#         straightforward to implement. In the future we may try out using Voronoi
#         teslation.

#         Args:
#             x_attribute (str): The name of the RepeatedShot attribute to use for
#                 the x-axis.
#             y_attribute (str): The name of the RepeatedShot attribute to use for
#                 the y-axis.
#             z_attribute (str): The name of the RepeatedShot attribute to use for
#                 the z-axis.
#             axes (matplotlib.axes._subplots.AxesSubplot, optional):
#                 (Default=None) The axes on which the data should be plotted. If
#                 set to None, new axes on a new figure will be used.
#             data_constraints (list of constraints): (Default=()) This argument
#                 is passed on to self.get_filtered_repeatedshot_list() and can be
#                 used to constrain which RepeatedShot instances are included in
#                 the returned lists. See that method's documentation for more
#                 information.
#             plot_contours (bool, optional): (Default=True) If set to True,
#                 contour lines (lines of constant values of z_attribute) will be
#                 drawn over the color plot using matplotlib's contour() function.
#                 If set to False, these contours will not be drawn. By default,
#                 the contours will be calculated by using scipy's griddata
#                 function to interpolate the data with method='cubic'.
#             contourf_args (dict, optional): (Default={}) Keyword-style arguments
#                 can be passed to matplotlib's contourf function (the one that is
#                 used for the colorplots) by including them in this dictionary.
#                 Note that the name of the arguments should be specifed as
#                 strings, so this can be something like {'hatches':'/'}.
#             contour_args (dict, optional): (Default={}) Analogous to the
#                 argument contourf_args, except that the keyword arguments
#                 provided in contour_args are passed to matplotlib's contour()
#                 function, which is responsible for plotting the contour lines of
#                 constant z_parameter values. These lines are only plotted when
#                 plot_contours is set to True.

#         Returns:
#             axes (matplotlib.axes._subplots.AxesSubplot): The axes on which the
#                 plot was made.
#         """
#         # Get arrays of values for the attributes.
#         attribute_list = [x_attribute, y_attribute, z_attribute]
#         x_values, y_values, z_values = self.get_repeatedshot_values(  # pylint: disable=unbalanced-tuple-unpacking
#             attribute_list, data_constraints)
#         x_values = np.array(x_values)
#         y_values = np.array(y_values)
#         z_values = np.array(z_values)

#         # Get axes and figure ready.
#         if not axes:
#             fig = plt.figure()
#             axes = fig.add_subplot(111)
#         fig = axes.get_figure()

#         # Pick limits for plot,
#         x_min, x_max = min(x_values), max(x_values)
#         y_min, y_max = min(y_values), max(y_values)
#         x_data_spread = x_max - x_min
#         y_data_spread = y_max - y_min
#         xlims = [x_min - 0.1 * x_data_spread, x_max + 0.1 * x_data_spread]
#         ylims = [y_min - 0.1 * y_data_spread, y_max + 0.1 * y_data_spread]

#         # Make the color plot using nearest-neighbor interpolation on a grid.
#         x_image = np.linspace(xlims[0], xlims[1], 101)
#         y_image = np.linspace(ylims[0], ylims[1], 101)
#         z_image = griddata((x_values, y_values), z_values,
#                            (x_image[None, :], y_image[:, None]),
#                            method='nearest')
#         # Add keyword arguments without overwriting the user's.
#         contourf_args = {
#             'levels': 50,
#             'cmap': plt.get_cmap('jet'),
#             **contourf_args,
#         }
#         contourf_plot = axes.contourf(
#             x_image, y_image, z_image, **contourf_args)

#         # Plot the contour lines as well if requested.
#         if plot_contours:
#             z_contours = griddata((x_values, y_values), z_values,
#                                   (x_image[None, :], y_image[:, None]),
#                                   method='cubic')
#             # Add keyword arguments without overwriting the user's.
#             contour_args = {
#                 'levels': 10,
#                 'linewidths': 0.5,
#                 'colors': 'k',
#                 'linestyles': 'solid',
#                 **contour_args,
#             }
#             axes.contour(x_image, y_image, z_contours, **contour_args)

#         # Add colorbar, labels, etc.
#         fig.colorbar(contourf_plot)
#         axes.set_xlabel(x_attribute)
#         axes.set_ylabel(y_attribute)

#         # Make name of labscript the title for the plot. Typically all of the
#         # shots will be from the same labscript, just with different values for
#         # globals, so we'll just take the name of the labscript from one shot.
#         # We'll also add the name of the z-axis parameter.
#         axes.set_title(self.last_shot.labscript + "\n" + z_attribute)

#         # Return the axes of the plot.
#         return axes
