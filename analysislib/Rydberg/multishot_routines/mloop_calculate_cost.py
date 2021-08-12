"""Calculate M-LOOP cost and uncertainty using predefined functions.

This script includes some predefined functions that generate costs and cost
uncertainties for M-LOOP optimization using data from runs of the experiment. A
given pair of functions that calculate the cost and uncertainty can be selected
using the mloop_cost_function_name global, which should be set to one of the
values listed below.

Possible values for the mloop_cost_function_name global (include the quotes):

* 'atom_number'
  * This gives a simple optimization of the atom number, and the uncertainty is
    simply calculated from the variance of the atom number between shots. If
    there is only one shot per M-LOOP iteration, then the uncertainty is set to
    zero.
* 'psd_3d_proxy_peak_od'
  * In order to use this cost, add a global called mloop_cost_atom_threshold and
    set it to a reasonable minimum atom number to aim for. It is used to
    suppress noise in the cost function at low atom numbers.
  * This function attempts to provide a cost that mimics the peak PSD of the
    cloud, assuming a 3D thermal gas. To avoid issues with fits converging, this
    function calculates a proxy for the PSD based on the peak optical depth of
    the image of the cloud instead of using any results from fits.
  * The peak OD of a 3D gas after a fixed time of flight expansion depends on
    the in-trap cloud size and the thermal velocity of the atoms, both of which
    scale with the square root of temperature T. Given that this occurs in two
    directions, and given that it also scales with atom number N, the peak OD
    scales as N/sqrt(T)**2 = N/T. Therefore (peak_od)**3/N**2 scales as N/T**3,
    which is proportional to the PSD at a fixed trap geometry.
  * Simply optimizing (peak_od)**3/N**2 isn't likely to work well because a shot
    with nearly 0 atoms but some noise can have a large value for that figure of
    merit due to the 1/N**2 scaling. To work around that another function is
    used to suppress the value of that expression for small atom numbers. The
    formula used for that is 2. / (np.exp(atom_threshold / atom_number) + 1.)
    where atom_threshold is a constant set by the mloop_cost_atom_threshold
    global. This function is based on the forumla for the excited state
    population of a two-level system in thermal equilibrium where atom_threshold
    plays the role of the energy splitting between the two levels, and the atom
    number plays the role of the temperature. The main difference is that it is
    multiplied by a factor of two so that it approaches 1 in the large atom
    number limit. At low atom numbers the function is exponentially suppressed.
    For large atom numbers that function saturates to 1, so it doesn't affect
    the cost in that regime. Due to noise, sometimes the measured atom number
    can be less than zero, and in that case the cost is just set to zero.
  * The cost as described thus far can easily become a very small number, say
    ~1e-12 due to the fact that the peak od is often order ~0.1 and the atom
    number can be quite large. Having a cost that small seems to mess up the
    numerics in M-LOOP, at least with the neural net learner in version 2.2.0.
    To avoid that, the cost is scaled up with the goal of getting it closer to
    ~1. To do that, it is assumed that a typical peak od is 0.1 and a typical
    atom number is the value of the mloop_cost_atom_threshold global, and the
    measured values are scaled relative to those typical values. This increases
    the calculated cost by a scale factor of 1000*mloop_cost_atom_threshold.
  * To reduce noise, the peak OD is actually calculated by taking the average of
    the pixels with the largest OD. The number pixels to average is controlled
    by the `mloop_n_peak_pixels_average` global. For example, setting that
    global to 10 will instruct this script to take the pixels with the 10
    largest ODs and average those ODs to calculate the peak OD. Setting that
    global to 1 will instruct this script to just use the OD of the single pixel
    with the largest OD. Setting `mloop_n_peak_pixels_average` to a small value,
    such as 1, will increase the measurement noise. Setting it too high can
    cause pixels with ODs much lower than the peak value to be included in the
    average, which will make the peak OD estimate inaccurate.
  * The overall cost is then calculated by multiplying the PSD proxy
    (peak_od)**3/N**2 by the low-atom-number-suppression function
    2. / (np.exp(atom_threshold / atom_number) + 1.) and by the constant scale
    factor 1000*mloop_cost_atom_threshold, or it is set to zero if the measured
    atom number is negative.
  * An uncertainty could be calculated via error propagation, but as of yet this
    hasn't been done and the uncertainty is simply always set to the value of
    the global mloop_cost_constant_uncertainty. See the docstring for
    constant_uncertainty() in this lyse script for more details.
  * Note that this method doesn't actually scale with the PSD when there is a
    BEC. In fact, for a pure BEC this cost scales as 1/N^(1/5) (i.e. when
    varying the atom number at zero temperature) ignoring the low-atom cutoff.
    Put another way, this cost function will make the optimizer prefer a small
    pure BEC over a large pure BEC, which isn't ideal.
    * The 1/N^(1/5) scaling for a pure BEC can be derived as follows, using some
      results from "Theory of Bose-Einstein condensation in trapped gases" by
      Dalfovo et al.
    * The peak OD scales as N/A where A is the area of the cloud after expansion
      in time of flight. A scales as v^2 where v is the expansion velocity, so
      the peak OD scales as N/v^2
    * The expansion energy (per particle) for a pure BEC is proportional to the
      chemical potential mu. The expansion energy is proportional to the
      expansion velocity squared (KE = 1/2 m v^2), so the peak OD scales as
      N/v^2 ~ N/KE ~ N/mu
    * The chemical potential for a pure BEC in a harmonic trap scales as N^(2/5)
      (see eqn 51 of the paper mentioned above). Therefore the peak OD of the
      cloud scales as N/mu ~ N/N^(2/5) ~ N^(3/5)
    * The proxy psd scales as (peak_od)^3/N^2 ~ N^(9/5)/N^2 ~ 1/N^(1/5).
* 'bec_number_proxy'
  * This cost function is designed to scale as N for a pure BEC.
  * The 'psd_3d_proxy_peak_od' cost function actually scales as 1/N^(1/5) for
    pure BECs (neglecting the low-atom number cutoff function, see above). This
    cost function calculates the psd proxy cost function, then multiplies it by
    N^(6/5).
  * Because this cost is calculated by first calculating the psd proxy cost
    function, it also uses the same low-atom-number cutoff function.
  * The atom number is normalized to the atom number threshold first to keep the
    cost closer to ~1, though that corresponds to multiplying the cost by a
    constant scaling factor and shouldn't have any effect on the optimization.
  * The overall scaling of this cost function (negelecting the low-atom-number
    cutoff) is therefore (peak_od)^3/N^(4/5).
    * Given that scaling, it's clear that this cost function promotes more
      peaked distributions since they have a larger peak OD for a given N. The
      reduction in cost for increasing N at fixed peak OD is less for this
      cost function than for the psd proxy cost function, so it doesn't
      emphasize peaked-ness as much. This is good to know when considering how
      it assigns costs to thermal/bimodal clouds.
* 'bec_root_n_proxy'
  * This is analogous to 'bec_number_proxy' except that the power of N is chosen
    so that the cost scales as N^(1/2) at zero temperature.
  * Compared to the 'bec_number_proxy', this cost function more heavily
    emphasizes the peak OD so it does a better job of getting rid of thermal
    cloud atoms to get a purer BEC. The cost still increases with increasing
    BEC number, so it favors larger BECs over smaller BECs.
* 'bec_fourth_root_n_proxy'
  * This is similar to 'bec_root_n_proxy' except that the power of N is chosen
    so that the cost scales as N^(1/4) at zero temperature.
  * This makes the cost function emphasize peak OD even more heavily than
    'bec_root_n_proxy' while still favoring larger BECs over smaller BECs.

To add additional cost and uncertainty functions to this module, complete the
following steps:

* Define functions for the new cost and/or uncertainty in this script.
  * The functions should take an instance of the RepeatedShot class as their
    only argument.
  * It's possible to use the same function in multiple cost/uncertainty pairs.
    In particular, the constant_uncertainty() function can be used as the
    uncertainty function if no uncertainty can be calculated. It just alwyas
    sets the uncertainty to be the value of the mloop_cost_constant_uncertainty
    global.
* Add an entry to cost_function_dict.
  * The key should be the string that the user should use to select the new
    cost/uncertainty pair.
  * The value should be a tuple with two elements. The first should be the
    function that calculates the cost, and the second should be the function
    that calculates the cost's uncerainty.
* Add the cost function key to this script's docstring so that users know that
  it is an option.

Note that multishot routines in general run after the singleshot routines, which
means that a copy of the shot file will have been transferred over to the
analysis computer by transfer_files.py before this script is run, which means
that there are two copies of the file. We typically save any additional results
just to the copy on the analysis computer since that's the copy we use, but the
M-LOOP integration code will look for results in the original copy. Results
calculated here are saved to both copies using save_result_to_both_copies() from
multishot_utils.py. That way the M-LOOP integration code still works, but we
still get a complete copy of the shot file on the analysis computer.
"""
import numpy as np

from analysislib.RbLab.lib.data_classes import Dataset, Shot
from analysislib.RbLab.lib.multishot_utils import (
    check_all_shots_run, check_all_singleshot_run, get_dataframe_subset,
    save_result_to_both_copies,
)


# Define possible cost and uncertainty functions:
def atom_number(repeatedshot):
    return repeatedshot.atom_number


def atom_number_uncertainty(repeatedshot):
    """Set the uncertainty to the atom number uncertainty if available.

    This sets the uncertainty to repeatedshot.atom_number_uncertainty if it is
    available. If there is only one shot in the RepeatedShot instance, then the
    value of repeatedshot.atom_number_uncertainty will be nan, which causes
    issues for M-LOOP. In that case we'll just set the uncertainty to zero
    instead.

    Args:
        repeatedshot (RepeatedShot): An instance of the RepeatedShot class from
            analysislib.RbLab.lib.data_classes for which the uncertainty should
            be calculated.

    Returns:
        uncertainty (float): The uncertainty, which is set to the value of
            repeatedshot.atom_number_uncertainty, unless that is nan in which
            case zero is returned instead.
    """
    uncertainty = repeatedshot.atom_number_uncertainty
    if np.isnan(uncertainty):
        return 0
    else:
        return uncertainty


def psd_3d_proxy_peak_od(repeatedshot):
    # Set constant parameters
    TYPICAL_PEAK_OD = 0.1

    # Extract results and settings from repeatedshot.
    atom_number = repeatedshot.atom_number
    atom_threshold = repeatedshot.mloop_cost_atom_threshold
    n_peak_pixels_average = repeatedshot.mloop_n_peak_pixels_average

    # Average the OD of the pixels with the highest OD. The number of pixels to
    # average is set by the mloop_n_peak_pixels_average global.
    od_image = repeatedshot.od_image
    sorted_array = np.sort(od_image, axis=None)
    mean_largest = np.mean(sorted_array[-n_peak_pixels_average:])
    peak_od = mean_largest

    # Scale peak_od and atom_number to make the resulting cost ~1. Otherwise it
    # can end up very small, say order ~1e-12, which can cause numerics issues
    # for M-LOOP, or at least its neural net learner as of version 2.2.0.
    peak_od_prime = peak_od / TYPICAL_PEAK_OD
    atom_number_prime = atom_number / atom_threshold

    # Calculate the proxy for the PSD.
    psd_proxy = peak_od_prime**3 / atom_number_prime**2

    # Calculate the thresholding function to suppress noise in the cost at low
    # atom numbers.
    if atom_number >= 0:
        thresholding_value = 2. / (np.exp(atom_threshold / atom_number) + 1.)
    else:
        thresholding_value = 0.

    # Combine to get the cost.
    cost = psd_proxy * thresholding_value
    return cost


def bec_number_proxy(repeatedshot):
    # Extract results and settings from repeatedshot.
    atom_number = repeatedshot.atom_number
    atom_threshold = repeatedshot.mloop_cost_atom_threshold

    # The psd_proxy scales as 1/N^(1/5) for a pure BEC (neglecting the low atom-
    # number cutoff). So multiply it by N^(6/5).
    psd_proxy = psd_3d_proxy_peak_od(repeatedshot)
    atom_number_prime = atom_number / atom_threshold
    # Set it atom number to 0 if it was measured to be a negative value.
    atom_number_prime = max(0, atom_number_prime)

    # PSD proxy scales as 1/N^(1/5) at T=0, so need to multiply it by N^(6/5) to
    # get something that scales as N at T=0.
    cost = psd_proxy * (atom_number_prime)**(6. / 5.)

    return cost


def bec_root_n_proxy(repeatedshot):
    # Extract results and settings from repeatedshot.
    atom_number = repeatedshot.atom_number
    atom_threshold = repeatedshot.mloop_cost_atom_threshold

    # The psd_proxy scales as 1/N^(1/5) for a pure BEC (neglecting the low atom-
    # number cutoff). So multiply it by N^(6/5).
    psd_proxy = psd_3d_proxy_peak_od(repeatedshot)
    atom_number_prime = atom_number / atom_threshold
    # Set it atom number to 0 if it was measured to be a negative value.
    atom_number_prime = max(0, atom_number_prime)

    # PSD proxy scales as 1/N^(1/5) at T=0, so need to multiply it by
    # N^(1/5)*N^(1/2) = N^(7/10) to get something that scales as N^(1/2) at T=0.
    cost = psd_proxy * (atom_number_prime)**(0.7)

    return cost


def bec_fourth_root_n_proxy(repeatedshot):
    # Extract results and settings from repeatedshot.
    atom_number = repeatedshot.atom_number
    atom_threshold = repeatedshot.mloop_cost_atom_threshold

    # The psd_proxy scales as 1/N^(1/5) for a pure BEC (neglecting the low atom-
    # number cutoff). So multiply it by N^(6/5).
    psd_proxy = psd_3d_proxy_peak_od(repeatedshot)
    atom_number_prime = atom_number / atom_threshold
    # Set it atom number to 0 if it was measured to be a negative value.
    atom_number_prime = max(0, atom_number_prime)

    # PSD proxy scales as 1/N^(1/5) at T=0, so need to multiply it by
    # N^(1/5)*N^(1/4) = N^(9/20) = N^0.45 to get something that scales as
    # N^(1/4) for a pure BEC.
    cost = psd_proxy * (atom_number_prime)**(0.45)

    return cost


def constant_uncertainty(repeatedshot):
    """Set the uncertainty to the value of mloop_cost_constant_uncertainty.

    If constant_uncertainty() is used but a good value for uncertainty isn't
    known, simply set mloop_cost_constant_uncertainty to zero. In that case,
    M-LOOP will automatically set it to minimum_uncertainty. The default value
    of minimum_uncertainty is very small which can lead to overfitting, so
    you'll likely want to set cost_has_noise to True for optimizations where the
    uncertainty is set to zero.

    Args:
        repeatedshot (RepeatedShot): An instance of the RepeatedShot class from
            analysislib.RbLab.lib.data_classes for which the uncertainty should
            be calculated.

    Returns:
        uncertainty (float): The uncertainty, which is set to the value of the
            global mloop_cost_constant_uncertainty.
    """
    return repeatedshot.mloop_cost_constant_uncertainty


# Create a dictionary for looking up the cost and uncertainty functions. The
# keys are the allowed values of the mloop_cost_function_name global. The values
# are tuples where the first entry is the function that calculates the cost, and
# the second entry is the function that calculates the uncertainty of the cost.
cost_function_dict = {
    'atom_number': (atom_number, atom_number_uncertainty),
    'psd_3d_proxy_peak_od': (psd_3d_proxy_peak_od, constant_uncertainty),
    'bec_number_proxy': (bec_number_proxy, constant_uncertainty),
    'bec_root_n_proxy': (bec_root_n_proxy, constant_uncertainty),
    'bec_fourth_root_n_proxy': (bec_fourth_root_n_proxy, constant_uncertainty),
}


# Get a subset of the Lyse dataframe containing only the shots to analyze.
df_subset = get_dataframe_subset(n_sequences_to_include=1)

# Check if the all of the shots from this call to engage in runmanager have
# completed.
all_shots_run = check_all_shots_run(df_subset)

# Check if the single shot routines have been run on all the shots from this
# call to engage in runmanager. Since the results here depend on results from
# on_the_fly_absorption_image_processing.py we have to make sure that the single
# shot routines run on all of the shots before we give results to M-LOOP.
# Sometimes a shot can be added after lyse starts running the multishot
# routines. That can lead to a scenario where all the shots have run but the
# single shot routines haven't been run on one or more of them.
all_singleshot_run = check_all_singleshot_run(df_subset)

# Create an instance of our custom Shot class. This class inherits from lyse.Run
# so it has all of that class's methods and more, and so it can be used in place
# of the lyse.Run class. We'll use the original copy since the M-LOOP script
# will look for results in that file.
shot_path = df_subset['filepath'].iloc[-1]
last_shot = Shot(shot_path)

# Set where results are saved for that shot file
results_group = 'results/mloop_costs'

if all_shots_run and all_singleshot_run:
    # All of the shots have completed, so do the analysis and save the result
    # for mloop_multishot.py
    print("All shots of engage have completed, generating results for mloop...")

    # Construct a Dataset instance
    dataset = Dataset(df_subset)

    # Do the standard analysis to get atom number, etc.. We won't redo the
    # absorption image processing, but we'll average and integrate the previous
    # results for individual shots.
    dataset.average_od_images()
    dataset.integrate_od_images()
    dataset.fit_gaussians()

    # Assume that there is only one repeatedshot instance in the dataset for
    # now. Later we may generalize to allow more than one repeatedshot to
    # analyze time-of-flight scan data, etc..
    repeatedshot = dataset.repeatedshot_list[0]

    # Get the functions corresponding to the cost specified by the global
    # mloop_cost_function_name.
    key = repeatedshot.mloop_cost_function_name
    cost_function, uncertainty_function = cost_function_dict[key]

    # Evaluate the cost and uncertainty
    cost = cost_function(repeatedshot)
    uncertainty = uncertainty_function(repeatedshot)

    # Save cost.
    save_result_to_both_copies(
        last_shot,
        'mloop_cost',
        cost,
        group=results_group,
    )
    # Save uncertainty with naming convention required by the mloop lyse
    # integration code.
    save_result_to_both_copies(
        last_shot,
        'u_mloop_cost',
        uncertainty,
        group=results_group,
    )

    # Print results.
    print(f"Cost: {cost} +/- {uncertainty}")
else:
    # In this case we're not ready for M-LOOP yet so we'll avoid running the
    # M-LOOP analysis. We don't need to save results in this case. The M-LOOP
    # integration code will just get nan for mloop_cost and u_mloop_cost since
    # their entries are empty in the dataframe, then it won't run.
    if not all_shots_run:
        print("Not all shots have run, skipping M-LOOP.")
    elif not all_singleshot_run:
        print("Single shot routines haven't run on all shots, skipping M-LOOP.")
