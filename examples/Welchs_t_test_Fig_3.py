#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 26 19:07:45 2025

@author: selinbac
"""

#USER DEFINED
plot_heat_map=True

import pandas as pd
import numpy as np
from scipy.stats import t
from itertools import combinations
from scipy.stats import ttest_ind
import re
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib as mpl



summary_df = pd.read_excel('../dataset/results_for_t_test.xlsx')
summary_df['Rh %'] = pd.to_numeric(summary_df['Rh %'], errors='coerce')
summary_df['Temperature (C)'] = pd.to_numeric(summary_df['Temperature (C)'], errors='coerce')
summary_df['Method'] = summary_df['Method'].str.upper()

metrics_to_analyze = [col for col in summary_df.columns if any(stat in col for stat in ['initial', 'final', 'slope','AUC'])]
percent_metrics = [col for col in metrics_to_analyze if '%' in col or any(k in col.lower() for k in ['conversion', 'selectivity', 'yield'])]
nonpercent_metrics = list(set(metrics_to_analyze) - set(percent_metrics))

# Groups: Temperature (1), Rh loading (2), and synthesis method (3)
group_definitions = [
    (1, '400/500/600C with 2% Rh', lambda df: (df['Rh %'] == 2.0) & df['Temperature (C)'].isin([400, 500, 600])),
    (2, '0.1/0.3/2% Rh at 500C with WI', lambda df: (df['Temperature (C)'] == 500) & df['Rh %'].isin([0.1, 0.3, 2.0]) & (df['Method'] == 'WI')),
    (3, '0.3% Rh with WI and NP', lambda df: (df['Rh %'] == 0.3) & df['Method'].isin(['WI', 'NP']))
]

grouped_rows = []
for group_num, description, condition_func in group_definitions:
    matched = summary_df[condition_func(summary_df)].copy()
    matched['Group #'] = group_num
    matched['Group Description'] = description
    matched['Subgroup'] = matched.groupby(['Rh %', 'Temperature (C)', 'Method']).ngroup()
    matched['Subgroup Label'] = matched['Group #'].astype(int).astype(str) + matched['Subgroup'].rank(method='dense').astype(int).apply(lambda x: chr(96 + x))
    grouped_rows.append(matched)

grouped_df = pd.concat(grouped_rows, ignore_index=True)
subgroup_sort_key = lambda x: (int(x[:-1]), x[-1]) if isinstance(x, str) and x[:-1].isdigit() else (float('inf'), '')
grouped_df = grouped_df.sort_values(by='Subgroup Label', key=lambda col: col.map(subgroup_sort_key)).reset_index(drop=True)



pairwise = []


# Loop over each unique group and metric
for group_num in grouped_df["Group #"].unique():
    group_df = grouped_df[grouped_df["Group #"] == group_num]
    subgroups = sorted(group_df["Subgroup Label"].unique(), key=subgroup_sort_key)

    for sg1, sg2 in combinations(subgroups, 2):
        df1 = group_df[group_df["Subgroup Label"] == sg1]
        df2 = group_df[group_df["Subgroup Label"] == sg2]
        
        for metric in metrics_to_analyze:
            vals1 = df1[metric].dropna()
            vals2 = df2[metric].dropna()
            if len(vals1) < 2 or len(vals2) < 2:
                continue

            
            t_stat, p_val = ttest_ind(vals1, vals2, equal_var=False)
            

            pairwise.append({
                "Group #": group_num,
                "Subgroup Pair": f"{sg1} vs {sg2}",
                "Metric": metric,
                "p-value": p_val,
                "Confidence (1 - p)": 1 - p_val
            })


pairwise_df = pd.DataFrame(pairwise)



for col in ["p-value", "Confidence (1 - p)"]:
    pairwise_df[col] = pd.to_numeric(pairwise_df[col], errors="coerce")


idx = pairwise_df.groupby(["Group #", "Metric"])["Confidence (1 - p)"].idxmin()


min_rows = (
    pairwise_df.loc[idx, ["Group #", "Metric", "Subgroup Pair", "p-value", "Confidence (1 - p)"]]
      .rename(columns={
          "Subgroup Pair": "Min CI Between",
          "Confidence (1 - p)": "Min Confidence"
      })
      .sort_values(["Group #", "Metric"])
      .reset_index(drop=True)
)
min_CI = pd.DataFrame(min_rows)


excel_path = './CI.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    grouped_df.to_excel(writer, sheet_name='Grouped Data', index=False)
    pairwise_df.to_excel(writer, sheet_name='CI', index=False)
    min_CI.to_excel(writer, sheet_name='min_CI', index=False)


# %% Heatmap
mpl.rcParams['font.family'] = 'Arial'
mpl.rcParams['axes.labelsize'] = 20
mpl.rcParams['axes.titlesize'] = 20
mpl.rcParams['xtick.labelsize'] = 17
mpl.rcParams['ytick.labelsize'] = 18
mpl.rcParams['legend.fontsize'] = 16
mpl.rcParams['mathtext.fontset'] = 'custom'
mpl.rcParams['mathtext.rm'] = 'Arial'
mpl.rcParams['mathtext.it'] = 'Arial:italic'
mpl.rcParams['mathtext.bf'] = 'Arial:bold'

if plot_heat_map:


    file_path = "./CI.xlsx"
    sheet_name = "min_CI"
    
    group_map = {1: "Temperature", 2: "Rh loading", 3: "Synthesis method"}
    column_order = ["Temperature","Rh loading", "Synthesis method"]
    
    
    DESCRIPTOR_PATTERNS = [
        (r"CO2\s*Conversion", "CO2 Conversion (%)"),
        (r"\bCO\s*Rate|\bCO\s+Net\s+Production", "CO Rate"),
        (r"CO\s*Selectivity|Selectivity\s*to\s*CO", "CO Selectivity"),
        (r"\bCH4\s*Rate|\bCH4\s+Net\s+Production", "CH4 Rate"),
    ]
    
    
    descriptor_priority = {
        "CO2 Conversion (%)": 0,
        "CO Rate": 1,
        "CO Selectivity": 2,
        "CH4 Rate": 3,
    }
    kind_priority = {
        "Initial": 0,          
        "Initial Slope": 1,
        "Final": 2,            
        "Final Slope": 3,
        "Overall Slope": 4,
        "AUC": 5
    }
    
    def normalize_descriptor(metric: str) -> str:
        for pat, name in DESCRIPTOR_PATTERNS:
            if re.search(pat, metric, flags=re.I):
                return name
        return metric   
    
    def split_kind(metric: str) -> str:
        for k in ["Initial Slope", "Final Slope", "Initial", "Final", "Overall Slope","AUC"]:
            if re.search(rf"\b{k}\b", metric, flags=re.I):
                return k
        return "Unspecified"


    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df["Group"] = df["Group #"].map(group_map)
    df = df[~df["Metric"].str.contains(r"CH4\s*Rate", flags=re.I, na=False)]
    
    df["Kind"] = df["Metric"].apply(split_kind)
    df["Descriptor"] = df["Metric"].apply(normalize_descriptor)
    df = df[~df["Kind"].isin(["Initial Slope", "Final Slope"])]
    df["descriptor_order"] = df["Descriptor"].map(descriptor_priority)
    df["kind_order"] = df["Kind"].map(kind_priority)
    df = df.sort_values(["kind_order", "descriptor_order", "Descriptor", "Kind"])
    
    df["Metric (ordered)"] = df["Kind"] + "  " + df["Descriptor"] 

    replacements = {
        "CO2 Conversion (%)": r"$\chi_{CO_2}$",
        "CO Rate": r"$r_{CO}$",
        "CO Selectivity": r"$S_{CO}$",
        "CH4 Rate": r"$r_{CH_4}$",
        "AUC": r"AUC" 
    }
    
    for long, short in replacements.items():
        df["Metric (ordered)"] = df["Metric (ordered)"].str.replace(
            long, short, regex=False
        )


    pivot_df = df.pivot(index="Metric (ordered)", columns="Group", values="Min Confidence")
    pivot_df = (pivot_df * 100).clip(0, 100)  
    
    present_cols = [c for c in column_order if c in pivot_df.columns]
    pivot_df = pivot_df.reindex(columns=present_cols)
    
    pivot_df = pivot_df.reindex(index=df["Metric (ordered)"].unique())
    
    plt.figure(figsize=(12, max(6, len(pivot_df) * 0.5)))
    ax = sns.heatmap(
    pivot_df, annot=True, fmt="", annot_kws={"size": 18}, cmap="RdYlGn", vmin=0, vmax=100, cbar_kws={"label": "Minimum Confidence Interval (%)"}
    )
    
    for tt in ax.texts:
        value = float(tt.get_text()) 
        tt.set_text(f"{value:.1f}" if value < 10 else f"{value:.0f}")  

    ax.xaxis.tick_top()
    ax.tick_params(axis='x', which='both', pad=8)
    ax.set_xticklabels(ax.get_xticklabels())#, rotation=45, ha='left')
    nrows, ncols = pivot_df.shape
    ax.set_aspect(ncols / nrows)
    plt.ylabel("")
    plt.xlabel("")
    plt.tight_layout()
    plt.savefig('heatmap.png', dpi=300)
    plt.show()
    
    
