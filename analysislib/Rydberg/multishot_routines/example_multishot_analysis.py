from lyse import data, path
import matplotlib.pyplot as plt

# Get a pandas dataframe containing all of the shots currently loaded in lyse.
df = data()

# Here's an example of how to access values of globals
z_coil_values = df['sideband_cool_z_coil']
print(type(z_coil_values))
print(z_coil_values)


# To save this result to the output hdf5 file, we have to instantiate a
# Sequence object:
# some_calculated_value =
# seq = Sequence(path, df)
# seq.save_result('some_calculated_value',some_calculated_value)
