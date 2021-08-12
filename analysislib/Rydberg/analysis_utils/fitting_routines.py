import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize
from scipy.ndimage import gaussian_filter1d

def gaussian(x, center, sigma, amplitude):
    """Evaluate a standard non-normalized gaussian without an offset.

    This function evaluates
    `amplitude * np.exp(-(x - center)**2 / (2 * sigma**2))`.

    Because the gaussian isn't normalized, the area under it is
    `A * np.sqrt(2 * np.pi * sigma**2)`.

    Args:
        x (np.ndarray): The x values at which to evaluate the gaussian.
        center (float): The position of the center of the gaussian.
        sigma (float): The sigma of the gaussian.
        amplitude (float): The height of the gaussian at its center. Note that
            this will NOT be divided by `np.sqrt(2 * np.pi * sigma**2)`.

    Returns:
        values (np.ndarray): The values of the gaussian with the specified
            parameters at the requested x values.
    """
    values = amplitude * np.exp(-(x - center)**2 / (2 * sigma**2))
    return values


def gaussian_with_offset(x, center, sigma, amplitude, offset):
    """Evaluate a standard non-normalized gaussian with an offset.

    This function evaluates
    `amplitude * np.exp(-(x - center)**2 / (2 * sigma**2)) + offset`.

    Because the gaussian isn't normalized, the area under it is
    `A * np.sqrt(2 * np.pi * sigma**2)` when the offset is zero.

    Args:
        x (np.ndarray): The x values at which to evaluate the gaussian.
        center (float): The position of the center of the gaussian.
        sigma (float): The sigma of the gaussian.
        amplitude (float): The height of the gaussian at its center relative to
            its offset. Note that this will NOT be divided by
            `np.sqrt(2 * np.pi * sigma**2)`.
        offset (float): The offset to add to the gaussian.

    Returns:
        values (np.ndarray): The values of the gaussian with the specified
            parameters at the requested x values.
    """
    values = amplitude * np.exp(-(x - center)**2 / (2 * sigma**2)) + offset
    return values


def gaussian_with_offset_jacobian(x, center, sigma, amplitude, offset,
                                  **kwargs):
    """Calculate the jacobian for `gaussian_with_offset()`.

    This method calculates the jacobian matrix which can be used when fitting
    `gaussian_with_offset()`.

    Args:
        x (np.ndarray): The x values at which to evaluate the jacobian.
        center (float): The position of the center of the gaussian.
        sigma (float): The sigma of the gaussian.
        amplitude (float): The height of the gaussian at its center relative to
            its offset. Note that this will NOT be divided by
            `np.sqrt(2 * np.pi * sigma**2)`.
        offset (float): The offset to add to the gaussian.

    Returns:
        jacobian (np.ndarray): The jacobian of the gaussian at the provided
            parameter values.
    """
    # Derivative with respect to center, chain rule
    col0 = amplitude * \
        np.exp(-(x - center)**2 / (2 * sigma**2)) * - \
        2 * (x - center) / (2 * sigma**2) * -1
    # Derivative with respect to sigma, chain rule
    col1 = amplitude * \
        np.exp(-(x - center)**2 / (2 * sigma**2)) * \
        2 * (x - center)**2 / (2 * sigma**3)
    # Derivative with respect to amplitude
    col2 = np.exp(-(x - center)**2 / (2 * sigma**2))
    # Derivative with respect to offset
    col3 = np.ones_like(x)

    # Combine into matrix
    jacobian = np.array([col0, col1, col2, col3])
    jacobian = jacobian.T
    return jacobian


# def fit_gaussian_log_iterative(cross_section, indices=None):
#     """Fit a guassian (no offset) to the data in cross_section.

#     """
#     # Creates indices if necessary
#     if indices is None:
#         indices = np.arange(len(cross_section))

#     # Take only the data points with positive values
#     keep_indices = (cross_section > 0)  # Array of booleans
#     positive_data = cross_section[keep_indices].astype(float)
#     log_positive_data = np.log(positive_data)
#     positive_indices = indices[keep_indices].astype(float)

#     def find_nearest(array, value):
#         array = np.asarray(array)
#         idx = (np.abs(array - value)).argmin()
#         return idx

#     smoothed_data = gaussian_filter1d(log_positive_data, sigma=1, mode='nearest')
#     center_guess = positive_indices[np.argmin(abs(smoothed_data))]
#     sigma_guess = abs(center_guess - positive_indices[find_nearest(smoothed_data, np.std(smoothed_data))])
#     amplitude_guess = np.min(smoothed_data)
#     offset_guess = np.max(smoothed_data)

#     try:

#         params, _ = scipy.optimize.curve_fit(gaussian_with_offset, positive_indices, smoothed_data, 
#                                                 p0=[center_guess, sigma_guess, amplitude_guess, offset_guess], maxfev=500)
#         success = True
#     except RuntimeError:
#         params = [0, 0, 0, 0]
#         success = False
#         print("Fit Failed")

#     center, sigma, amplitude, offset = params
#     return [center, sigma, amplitude, offset], success



def fit_gaussian_log_iterative(cross_section, indices=None,
                               min_iterations=10, max_iterations=100,
                               sigma_tolerance=1e-4):
    """Fit a guassian (no offset) to the data in cross_section.

    Uses the iterative algorithm from the paper "A Simple Algorithm for Fitting
    a Gaussian Function" by Hongwei Guo. Data points with negative values will
    be ignored. The fitting usually converges, but if the gaussian is too small
    or nonexistent, a numpy.linalg.LinAlgError with the message "Singular
    matrix" may be raised due to numerical issues in solving that algorithm's
    matrix equation.

    If indices is None, then they will be assumed to be
    [0, 1, ..., len(cross_section)]. This is only important for ensuring that
    the center position returned for the gaussian has the correct value.

    The fitting iterations will proceed until either max_iterations is reached
    or the fractional change in the fitted value for sigma from one iteration to
    the next becomes less than sigma_tolerance. For example, if sigma_tolerance
    is 1e-4 and one iteration estimates sigma = 10.0002 and the next iteration
    estimates sigma  = 10.0004 (a fractional change of about 2e-5) then the
    iterations will stop as long as min_iterations has been reached. Note that
    this does NOT imply that the estimate for sigma will be accurate to one part
    in 1e-4; it may be larger.

    Args:
        cross_section (np.ndarray): A 1D array giving the integrated cross
            section of the atomic cloud.
        indices (np.ndarray, optional): (Default = None) The indices (i.e.
            x-values) corresponding to the data in cross_section. If indices is
            None, then it will be assumed to be [0, 1, ..., len(cross_section)].
            This is important for ensuring that the center position returned for
            the gaussian has the correct value.
        min_iterations (int, optional): (Default = 10) The minimum number of
            fitting iterations to perform.
        max_iterations (int, optional): (Default = 100) The maximum number of
            fitting iterations to perform.
        sigma_tolerance (float, optional): (Default = 1e-4) A parameter to
            decide when the fit has converged. See the detailed function
            explanation above for more information.

    Returns:
        (tuple of floats): a tuple of the three fitted parameters
            (center, sigma, amplitude)
    """
    #cross_section = abs(cross_section)
    # Creates indices if necessary
    if indices is None:
        indices = np.arange(len(cross_section))

    # Take only the data points with positive values
    keep_indices = (cross_section > 0)  # Array of booleans
    positive_data = cross_section[keep_indices].astype(float)
    log_positive_data = np.log(positive_data)
    positive_indices = indices[keep_indices].astype(float)

    # Start the iterative fitting
    fitted_values = positive_data  # Use data for first iteration
    previous_sigma = 0.  # Initialize
    keep_iterating = True
    n_iterations = 0  # Keep track of number of iterations
    while keep_iterating:
        # Make the matrix from equation 16 of the paper
        def matrix_element_func(j, k): return (
            positive_indices**(j + k) * fitted_values**2).sum()
        left_matrix = [[matrix_element_func(j, k)
                        for j in range(3)] for k in range(3)]
        left_matrix = np.array(left_matrix)

        # Make the vector from the right side of equation 16 of the paper
        def vector_element_func(j): return (
            positive_indices**j *
            fitted_values**2 *
            log_positive_data).sum()
        right_vector = [vector_element_func(j) for j in range(3)]
        right_vector = np.array(right_vector)

        # Now solve the matrix equation and convert the fitted parabola
        # parameters into parameters of gaussian
        a, b, c = np.linalg.solve(left_matrix, right_vector)

        # Update fitted values
        fitted_values = np.exp(
            a +
            b *
            positive_indices +
            c *
            positive_indices**2)

        # Calculate sigma from the fit parameters to check convergence.
        if c < 0:
            sigma = np.sqrt(-1 / (2 * c))
        else:
            # Set to zero rather than using complex numbers
            sigma = 0

        # Stop iterating if we've converged
        if sigma > 0 and previous_sigma > 0:
            delta_sigma = abs(sigma - previous_sigma) / previous_sigma
            if delta_sigma < sigma_tolerance:
                keep_iterating = False
        previous_sigma = sigma

        # Stop iterating if we've hit max_iterations
        n_iterations += 1
        if n_iterations >= max_iterations:
            keep_iterating = False

        # Force iterations to continue if min_iterations hasn't been reached
        if n_iterations < min_iterations:
            keep_iterating = True

    # Convert the fitted parabola parameters into parameters of the gaussian
    if c < 0:
        center = -b / (2 * c)
        sigma = np.sqrt(-1 / (2 * c))
        amplitude = np.exp(a - b**2 / (4 * c))
    else:
        # Set values to np.nan if c > 0 (which would give imaginary sigma, which
        # is a sign that the fit didn't converge)
        center, sigma, amplitude = np.nan, np.nan, np.nan

    return center, sigma, amplitude



def fit_gaussian_with_offset(cross_section, indices=None,
                             fit_gaussian_log_iterative_args_dict={},
                             curve_fit_args_dict={}):
    """Fit a guassian (with offset) to the data in cross_section.

    This function uses this module's fit_gaussian_log_iterative() to get intial
    guesses for the gaussian fit parameters (except for the offset, which is
    initially guessed to be zero), then uses scipy's curve_fit() function to fit
    a gaussian with offset to cross_section. A function for evaluating the
    jacobian matrix of derivatives is passed to curve_fit() so that numerical
    differentiation isn't necessary.

    Args:
        cross_section (np.ndarray): A 1D array giving the integrated cross
            section of the atomic cloud.
        indices (np.ndarray, optional): (Default = None) The indices (i.e.
            x-values) corresponding to the data in cross_section. If indices is
            None, then it will be assumed to be [0, 1, ..., len(cross_section)].
            This is important for ensuring that the center position returned for
            the gaussian has the correct value.
        fit_gaussian_log_iterative_args_dict (dict): (Default = {}) Additional
            keyword arguments can be passed on to fit_gaussian_log_iterative()
            by including them as entries in this dictionary.
        curve_fit_args_dict (dict): (Default = {}) Additional keyword arguments
            can be passed on to curve_fit() by including them as entries in this
            dictionary.

    Returns:
        (tuple of floats): a tuple of the four fitted parameters
            (center, sigma, amplitude, offset)
    """
    # Creates indices if necessary
    if indices is None:
        indices = np.arange(len(cross_section))

    def find_nearest(array, value):
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return idx

    # Take only the data points with positive values
    keep_indices = (cross_section > 0)  # Array of booleans
    positive_data = cross_section[keep_indices].astype(float)
    log_positive_data = abs(np.log(positive_data))
    positive_indices = indices[keep_indices].astype(float)

    smoothed_data = gaussian_filter1d(log_positive_data, sigma=1, mode='nearest')
    center_guess = positive_indices[np.argmax(abs(smoothed_data))]
    offset_guess = np.min(smoothed_data)
    amplitude_guess = np.max(smoothed_data) - offset_guess
    sigma_guess = abs(center_guess - positive_indices[find_nearest(smoothed_data, amplitude_guess/np.e)])

    # Get initial parameter guesses (center, sigma, amplitude)
    initial_guesses = [center_guess, sigma_guess, amplitude_guess, offset_guess]

    # Do nonlinear fit least-squares optimization.
    fitted_parameters, _ = scipy.optimize.curve_fit(
        gaussian_with_offset, positive_indices, log_positive_data, p0=initial_guesses,
        jac=gaussian_with_offset_jacobian, **curve_fit_args_dict)

    # plt.figure()
    # plt.scatter(positive_indices, log_positive_data)
    # xpoints = np.linspace(np.min(positive_indices), np.max(positive_indices), 1000)
    # plt.plot(xpoints, gaussian_with_offset(xpoints, *fitted_parameters))
    return fitted_parameters
