# Overview

This repository contains a Python translation of the original Dynamic Factor Model (DFM) and GDP Nowcast framework developed by the Federal Reserve Bank of New York (FRBNY).
The original MATLAB code belongs to Eric Qian and Brandyn Bok and is available here:

Original NY Fed MATLAB code:
https://github.com/FRBNY-TimeSeriesAnalysis/Nowcasting

The Python translation and all adaptations belong to MK, available here:

Python translation by MK:
https://github.com/MajesticKhan/Nowcasting-Python

## Purpose of the Repository

For my Master’s thesis, I built a GDP nowcasting model that replicates the New York Fed’s methodology, with several modifications described in the thesis.
The objective is to evaluate whether the introduction of fiscal variables can improve GDP nowcast accuracy.

Files ending with _fiscal correspond to the version of the model that includes fiscal variables.
Files without _fiscal correspond to the baseline model without fiscal data (most, but not all, include the suffix _new).

## Folders and Files
- nowcast_yyyy.py: Generates the GDP nowcast for each year (baseline and fiscal versions).
- variables_creation.py: Creates and adds new variables to the dataset for testing alternative specifications.
- dashboard_nowcast_new.py: Visualizes the results of the updated model; a fiscal version is provided for the fiscal specification.
- Spec_US_new.xlsx: Model specification, defining variables, transformations, release lags, and block assignments (baseline and fiscal versions)
- data/: Contains all input data used in the models, downloaded from FRED. 
- Functions/: Core functions for loading data, estimating the DFM, and updating predictions; largely unchanged from the original NY Fed structure.
- DFM_new.py: Script for estimating the Dynamic Factor Model.
- DFM_quarter_param: Stores quarterly estimated DFM parameters.
- metrics_Q/: Contains quarterly accuracy metrics (including RMSE, MAE, Bias).
- news_Q/: Includes the news decomposition showing each variable’s contribution to weekly nowcast revisions.
- nowcast_Q/: Saves the nowcast output for each quarter.


## NOTICE:

# GDPnowcast-fiscal
