import sys
import os
import numpy as np

import pycatrobin.data.extract as ex
import pycatrobin.analysis.data_analysis as da

# Define the home directory and path to data
home_dir = os.path.expanduser("~")
path =  \
        "../dataset/finalized_RR_data/alldata"
        # "../dataset/finalized_RR_data/intra"
        # "../dataset/finalized_RR_data/alldata_temp"
        # "../dataset/finalized_RR_data/alldata_Rh_loading"
        # "../dataset/finalized_RR_data/alldata_synth"
        # "../dataset/finalized_RR_data/premix"

path_all = "../dataset/finalized_RR_data/alldata"

# Keywords to exclude
exclude_keywords = [
    "0p0005", # data with too low Rh mass, likely to be inaccurate
    "(1)",    # data mistakenly uploaded twice
    "PercentLoading_Synthesis_MassLoading_Temperature_Date_Location", # example Excel file
    # "_UCSB",  # data from UCSB
    # "_Cargnello", # data from Cargnello
    # "_SLAC",   # data from SLAC
    # "_PSU",
]
exclude_keywords_all = [
    "0p0005", # data with too low Rh mass, likely to be inaccurate
    "(1)",    # data mistakenly uploaded twice
    "PercentLoading_Synthesis_MassLoading_Temperature_Date_Location", # example Excel file
]

# Create an instance of DataForGP
dataset = ex.DataForGP(path=path)
dataset.find_excel_files()
dataset.filter_excel_files(exclude_keywords=exclude_keywords, verbose=True)
dataset.construct_dataframe(extensive=False)
# dataset.convert_measured_to_nominal(which_column="Rh_total_mass")
dataset.convert_measured_to_nominal(which_column="Rh_total_mass", allowed_values=np.array([0.02])) # for Round Robin data
dataset.apply_duplicate_groupid(
    exclude_columns=['filename', 'experiment_date', 'location'],
    verbose=False
)

# Create an instance of DataForGP for all data
dataset_all = ex.DataForGP(path=path_all)
dataset_all.find_excel_files()
dataset_all.filter_excel_files(exclude_keywords=exclude_keywords_all, verbose=True)
dataset_all.construct_dataframe(extensive=False)
# dataset.convert_measured_to_nominal(which_column="Rh_total_mass")
dataset_all.convert_measured_to_nominal(which_column="Rh_total_mass", allowed_values=np.array([0.02])) # for Round Robin data
dataset_all.apply_duplicate_groupid(
    exclude_columns=['filename', 'experiment_date', 'location'],
    verbose=False
)

# Calculate and add target values into the DataFrame
savgol=False
methods=[
    'AUC',
    'final value',
    'initial value',
    'final slope',
    'initial slope',
    'overall slope',
        ]

for column in [
   # 'CO2 Conversion (%)',
   # 'CH4 Net Production Rate (mol/molRh/s)',
   # 'CO Net Production Rate (mol/molRh/s)',
   # 'CO Forward Production Rate (mol/molRh/s)',
   'Selectivity to CO (%)'
    ]:
    dataset.assign_target_values(
        savgol=savgol, methods=methods,
        column=column, temp_threshold=3.5, init_tos_buffer=0.5, adjacency_slope=1.0,
        )
    dataset_all.assign_target_values(
        savgol=savgol, methods=methods,
        column=column, temp_threshold=3.5, init_tos_buffer=0.5, adjacency_slope=1.0,
        )

# Construct unique DataFrame using group IDs
dataset.construct_unique_dataframe(verbose=False)
dataset_all.construct_unique_dataframe(verbose=False)

# # Plot the data and the corresponding slopes
# dataset.plot_tos_data(column='CO2 Conversion (%)', #'Selectivity to CO (%)',
#                       x_max_plot=20, temp_threshold=3.5, init_tos_buffer=0.5, adjacency_slope=1.0,
#                       plot_selected=True, plot_slope=False,
#                       methods_slope=['initial slope', 'final slope', 'overall slope'], show=True,
#                       savgol=savgol,
#                       gui=True)

# Create an instance of DataAnalysis ------
analysis = da.DataAnalysis(dataset=dataset)
# Calculate statistics DataFrame on the basis of GroupID; it determines which data to use as entire dataset
analysis.calculate_statistics_duplicate_group(
    dataset_all=dataset_all,
    total='duplicate',
    verbose=False,
    average_same_location=False,
    # average_same_location=True, # for inter-lab analysis
)

# print(analysis.df_stat['CO Net Production Rate (mol/molRh/s)_final slope_mean'])
# print(analysis.df_stat[['CO Net Production Rate (mol/molRh/s)_auc_std', 'CO Net Production Rate (mol/molRh/s)_auc_mean']])

# analysis.plot_tos_data_duplicate(column='CO Net Production Rate (mol/molRh/s)', x_max_plot=12, y_max_plot=5.5)
# analysis.plot_tos_data_duplicate(column='CO Net Production Rate (mol/molRh/s)', x_max_plot=12, y_max_plot=10.5)
# analysis.plot_tos_data_duplicate(column='CO Net Production Rate (mol/molRh/s)', x_max_plot=12, font_scale=1.3)
# analysis.plot_tos_data_duplicate(column='CO Net Production Rate (mol/molRh/s)', x_max_plot=12, y_max_plot=23, font_scale=1.3) # for Old dataset
# analysis.plot_tos_data_duplicate(column='CO Forward Production Rate (mol/molRh/s)')
# analysis.plot_tos_data_duplicate(column='Selectivity to CO (%)', x_max_plot=12, y_max_plot=105)
# analysis.plot_tos_data_duplicate(column='CH4 Net Production Rate (mol/molRh/s)', x_max_plot=12, y_max_plot=10.5)
# analysis.plot_tos_data_duplicate(column='CO2 Conversion (%)', x_max_plot=12, y_max_plot=45)

# analysis.plot_heatmap(
#     which_to_plot='snr',
#     # which_to_plot='std_dev',
#     # which_to_plot='std_dev_mean_normalized',
#     # snr_type='std_dev',
#     # snr_type='range',
#     snr_type='mu_sigma',
#     cmap='Reds',
#     # cmap='Blues',
#     vmax=5.3,
#     # vmin=0.0,
# )

# average_value = analysis.df_snr.mean().mean()
# print(f'Average value of all the values in the DataFrame: {average_value}')

analysis.compare_targets_std_dev(
    target_wise=True,
    # snr_type='range', #'std_dev',
    snr_type='mu_sigma',
    plot_hist=True, #False,
    # save_fig=True,
    # prefix='',
)

# analysis._generate_data_distribution_horizontal(
#     column='CO Net Production Rate (mol/molRh/s)_initial value',
#     plot_hist=False
# )

# Export the processed data
# dataset.export_sheet(unique=True)
# dataset.export_sheet(unique=False)