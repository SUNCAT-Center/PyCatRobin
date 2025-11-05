import os
import glob
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from skfda import FDataGrid
from skfda.preprocessing.smoothing import BasisSmoother
from skfda.representation.basis import FourierBasis
from skfda.inference.anova import oneway_anova

# ------------------------------------------------------------------
# 1.  ── helpers ────────────────────────────────────────────────────
# ------------------------------------------------------------------
def find_stable_temperature_indices(df, window_size=3,
                                    temp_threshold=5.0, min_temp=100):
    """
    Detect the start/end indices where temperature is stable above `min_temp`.
    """
    temp = df.iloc[:, 1].values
    above_min = np.where(temp >= min_temp)[0]
    if not above_min.size:
        return 0, 0
    start_idx = above_min[0]

    # Find first window of stability
    for i in range(start_idx, len(temp) - window_size):
        win = temp[i:i + window_size]
        if win.max() - win.min() <= temp_threshold:
            # Find last window of stability
            for j in range(len(temp), i + window_size, -1):
                win = temp[j - window_size:j]
                if win.max() - win.min() <= temp_threshold:
                    return i, j
            return i, len(temp)
    return start_idx, len(temp)

# ------------------------------------------------------------------
# 2.  ── Permutation-based Functional ANOVA ─────────────────────────
# ------------------------------------------------------------------
def permutation_functional_anova(groups, n_permutations=1000, random_state=42):
    """
    Permutation-based functional ANOVA.
    groups: list of FDataGrid objects (one per group)
    Returns: observed_statistic, permutation_p_value
    """
    rng = np.random.default_rng(random_state)

    # Combine all curves and labels
    all_data = np.vstack([g.data_matrix.squeeze() for g in groups])
    labels = np.concatenate([[i]*len(g) for i, g in enumerate(groups)])

    # Compute observed statistic
    observed_stat, _ = oneway_anova(*groups)

    perm_stats = []
    for _ in range(n_permutations):
        perm_labels = rng.permutation(labels)
        perm_groups = []
        for i in np.unique(labels):
            perm_groups.append(FDataGrid(data_matrix=all_data[perm_labels == i],
                                         grid_points=groups[0].grid_points))
        stat, _ = oneway_anova(*perm_groups)
        perm_stats.append(stat)

    perm_stats = np.array(perm_stats)
    p_value = np.mean(perm_stats >= observed_stat)

    return observed_stat, p_value

# ------------------------------------------------------------------
# 3.  ── Functional ANOVA pipeline ──────────────────────────────────
# ------------------------------------------------------------------
def process_folder(folder_path: Path):
    """
    Process one folder: read data, trim by temperature stability,
    merge constants, summarize each file (including SLAC), run Functional ANOVA,
    and plot (including SLAC experiments).
    """
    print(f"\n▶ Processing “{folder_path.name}” …")

    # 3.1  Collect Excel files
    file_paths = glob.glob(str(folder_path / '*.xlsx')) + glob.glob(str(folder_path / '*.xls'))
    if not file_paths:
        print("  ↳ No XLS/XLSX files found — skipping.")
        return

    # 3.2  Temperature‐trimming
    dfs_by_file = {}
    for fp in file_paths:
        fn = Path(fp).stem
        try:
            df = pd.read_excel(fp, sheet_name='Data', engine='openpyxl')
            orig_len = len(df)
            s, e = find_stable_temperature_indices(df)
            df = df.iloc[s:e].reset_index(drop=True)
            dfs_by_file[fn] = df
            print(f"  ↳ {fn}: trimmed {s} start, {orig_len - e} end rows")
        except Exception as exc:
            print(f"  ↳ {fn}: {exc}")
    if not dfs_by_file:
        print("  ↳ No usable ‘Data’ sheets found — skipping.")
        return

    # 3.3  Read & reshape Constants sheets
    const_rows = []
    for fp in file_paths:
        tmp = pd.read_excel(fp, sheet_name='Constants', usecols=['Variable','Value'])
        row = tmp.set_index('Variable').T
        row['Source_File'] = Path(fp).stem
        const_rows.append(row)
    constants_df = pd.concat(const_rows, ignore_index=True)

    RENAME_MAP = {
        'pretreatement pressure':      'Pretreatment Pressure',
        'pretreatment pressure (bar)': 'Pretreatment Pressure',
        'bed length':                  'Bed Length',
        'location daily reaction number': 'LocationDailyReactionNumber',
    }
    constants_df = (
        constants_df
            .rename(columns=lambda c: c.strip())
            .rename(columns=lambda c: RENAME_MAP.get(c.lower(), c))
            .T.groupby(level=0).first().T
    )
    constants_df['Rh mass'] = (
        constants_df['Catalyst Mass'].astype(float)
        * constants_df['Weight Loading'].astype(float)
    )

    # 3.4  Per-file clean-ups & combine
    for file_id, df in dfs_by_file.items():
        df = df.iloc[5:].copy()
        if 'Time on stream (hrs)' in df.columns:
            df.rename(columns={'Time on stream (hrs)': 'Time on Stream (hr)'}, inplace=True)
        if 'Time on Stream (hr)' in df.columns:
            t0 = df['Time on Stream (hr)'].iloc[0]
            df['Time on Stream (hr)'] -= t0
        else:
            print(f"  ↳ {file_id}: missing ‘Time on Stream (hr)’")
        df = df[df['Time on Stream (hr)'] <= 10].reset_index(drop=True)
        df['Source'] = file_id
        dfs_by_file[file_id] = df

    combined_df = pd.concat(dfs_by_file.values(), ignore_index=True)
    constants_df['Source_File'] = constants_df['Source_File'].str.replace(r'\.xls[x]?$', '', regex=True)
    combined_df = combined_df.merge(constants_df, left_on='Source', right_on='Source_File', how='left') \
                             .drop(columns=['Source_File'], errors='ignore')
    combined_df.drop(columns=['Synthesis Batch','Reactor Number','Reactor Tube ID','Processing Script'],
                     inplace=True, errors='ignore')
    combined_df['experiment_no'] = combined_df['Source'].astype('category').cat.codes + 1
    cols = ['experiment_no'] + [c for c in combined_df.columns if c != 'experiment_no']
    combined_df = combined_df[cols]

    # 3.5  Functional ANOVA (Permutation)
    measure_col = combined_df.columns[5]
    labs = []
    curves_resampled = []

    # Define a uniform grid for interpolation
    common_time = np.linspace(0, 10, 100)

    for src, df in combined_df.groupby('Source'):
        lab = df['LocationDailyReactionNumber'].iloc[0]
        labs.append(lab)

        # Interpolate each curve to the common grid
        interp_vals = np.interp(common_time,
                                df['Time on Stream (hr)'].values,
                                df[measure_col].values)
        curves_resampled.append(interp_vals)

    curves = np.array(curves_resampled)
    time_points = common_time

    # Convert to functional data object
    fd = FDataGrid(data_matrix=curves, grid_points=time_points)

    # Smooth using Fourier basis
    basis = FourierBasis(domain_range=(time_points[0], time_points[-1]), n_basis=7)
    smoother = BasisSmoother(basis=basis)
    fd_smooth = smoother.fit_transform(fd)

    # Split smoothed data by lab into separate FDataGrid objects
    unique_labs = np.unique(labs)
    group_fd = []
    for lab in unique_labs:
        indices = np.where(np.array(labs) == lab)[0]
        group_fd.append(fd_smooth[indices])

    # Run permutation functional ANOVA
    statistic, p_value = permutation_functional_anova(group_fd, n_permutations=1000)
    print(f"  ↳ Permutation Functional ANOVA statistic = {statistic:.4f}, p-value = {p_value:.4f}")

    # 3.6  Plotting
    plt.figure(figsize=(10, 6))
    palette = {
        'Cargnello1': '#e41a1c',
        'Stanford':   '#e41a1c',
        'PSU':        '#6a3d9a',
        'UCSB':       '#1b9e77',
        'SLAC':       '#ff69b4',
    }

    for source, df_exp in combined_df.groupby('Source'):
        lab_id = df_exp['LocationDailyReactionNumber'].iloc[0]
        if lab_id.startswith('SLAC'):
            colour = palette['SLAC']
        else:
            lab_key = 'Stanford' if lab_id == 'Cargnello1' else lab_id
            colour = palette.get(lab_key, '#333333')

        plt.plot(
            df_exp['Time on Stream (hr)'],
            df_exp.iloc[:, 5],
            marker='o',
            label=source,
            color=colour
        )

    plt.xlabel('Time on Stream (hr)')
    plt.ylabel('Forward rate of RWGS (mol CO / mol Rh / s)')
    plt.title(f'RWGS forward-rate – {folder_path.name} (all labs)')
    plt.legend(title='File')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Run the pipeline on all folders in current directory
for sub in Path('../dataset/finalized_RR_data').iterdir():
    if sub.is_dir() and not sub.name.startswith('.'):
        process_folder(sub)
