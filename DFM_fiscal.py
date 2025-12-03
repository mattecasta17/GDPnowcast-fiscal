#-------------------------------------------------Libraries
import os
from datetime import datetime as dt
from Functions.load_spec import load_spec
from Functions.load_data import load_data
from Functions.dfm import dfm
import pickle
import pandas as pd



#-------------------------------------------------Set dataframe to full view
pd.set_option('display.expand_frame_repr', False)


#-------------------------------------------------User Inputs
vintages     = ['2017-01-03', '2017-04-03', '2017-07-03', '2017-10-02',
                '2018-01-02', '2018-04-02', '2018-07-02', '2018-10-01',
                '2019-01-02', '2019-04-01', '2019-07-01', '2019-10-01',
                '2020-01-02', '2020-04-01', '2020-07-01', '2020-10-01',
                '2021-01-01', '2021-04-01', '2021-07-01', '2021-10-01',
                '2022-01-03', '2022-04-01', '2022-07-01', '2022-10-03',
                '2023-01-03', '2023-04-03', '2023-07-03', '2023-10-02',
                '2024-01-02', '2024-04-01', '2024-07-01', '2024-10-01',
                '2025-01-02', '2025-04-01']
# vintage dataset to use for estimation
country      = 'US_fiscal'                                                           # United States macroeconomic data
sample_start = dt.strptime("2000-01-01", '%Y-%m-%d').date().toordinal() + 366 # estimation sample


#-------------------------------------------------Load model specification and dataset.
# Load model specification structure `Spec`
Spec = load_spec('Spec_US_fiscal.xlsx')

# Parse `Spec`
SeriesID         = Spec.SeriesID
SeriesName       = Spec.SeriesName
Units            = Spec.Units
UnitsTransformed = Spec.UnitsTransformed

# Load data
for vintage in vintages:
    datafile   = os.path.join('data',country,vintage + '.xlsx')
    X,Time,Z   = load_data(datafile,Spec,sample_start)


    # sanity check
    assert X.shape[1] == len(Spec.SeriesName), "X e Spec non allineati"


    #-------------------------------------------------Run dynamic factor model (DFM) and save estimation output as 'ResDFM'.
    threshold = 1e-4 # Set to 1e-5 for more robust estimates
    Res = dfm(X,Spec,threshold)
    Res = {"Res": Res,"Spec":Spec}

    #-------------------------------------------------Save output in dedicated folder
    output_dir = 'DFM_quarter_param_fiscal'
    os.makedirs(output_dir, exist_ok=True)
    file_name = 'ResDFM' + '_fiscal_' + vintage.replace('-', '') + '.pickle'
    output_path = os.path.join(output_dir, file_name)

    with open(file_name, 'wb') as handle:
        pickle.dump(Res, handle)
    # TODO: Res and Spec should be separate, this will be fixed after the unit tests are created
