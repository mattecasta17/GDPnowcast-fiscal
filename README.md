# Overview

This repository is built on the original Dynamic Factor Model (DFM) and GDP Nowcast framework developed by the Federal Reserve Bank of New York (FRBNY). The foundational MATLAB implementation was created by Eric Qian and Brandyn Bok, and forms the basis of the forecasting architecture used in this work.

Original NY Fed MATLAB code:
https://github.com/FRBNY-TimeSeriesAnalysis/Nowcasting

The present Python codebase is developed on top of the Python translation by MK, which served as the baseline reference for porting the FRBNY model into Python and for extending it with additional functionality—most notably, the integration of fiscal variables into the DFM.

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


## Disclaimer

This repository includes code that was partially developed, debugged, or refined with the assistance of AI-powered tools. While every effort has been made to ensure correctness, transparency, and reproducibility, the model and its extensions may still contain inaccuracies or aspects that can be improved.

Contributions, suggestions, or corrections are warmly welcomed.
If you notice any issue or have ideas for improvement, please feel free to contact me or open an issue on GitHub.

Matteo Castaldo
