"""Lists of models grouped by aspects."""
all_models = [
    'ConstantNaive',
    'LastValueNaive',
    'AverageValueNaive',
    'GLS',
    'GLM',
    'ETS',
    'ARIMA',
    'FBProphet',
    'RollingRegression',
    'GluonTS',
    'SeasonalNaive',
    'UnobservedComponents',
    'VARMAX',
    'VECM',
    'DynamicFactor',
    'MotifSimulation',
    'WindowRegression',
    'VAR',
    'TFPRegression',
    'ComponentAnalysis',
    'DatepartRegression',
    "UnivariateRegression",
    "Greykite",
    'UnivariateMotif',
    'MultivariateMotif',
    'NVAR',
    'MultivariateRegression',
    'SectionalMotif',
    'Theta',
    'ARDL',
    'NeuralProphet',
    'DynamicFactorMQ',
    'PytorchForecasting',
    'ARCH',
]
# downweight slower models
default = {
    'ConstantNaive': 1,
    'LastValueNaive': 1,
    'AverageValueNaive': 1,
    'GLS': 1,
    'SeasonalNaive': 1,
    'GLM': 1,
    'ETS': 1,
    'FBProphet': 0.3,
    # 'RollingRegression': 1,  # maybe not?
    'GluonTS': 0.1,  # downweight if that becomes an option
    'UnobservedComponents': 1,
    'VAR': 1,
    'VECM': 1,
    'WindowRegression': 0.5,
    'DatepartRegression': 1,
    # 'UnivariateRegression': 0.1,  # this has been crashing on 1135
    'MultivariateRegression': 0.2,
    'UnivariateMotif': 1,
    'MultivariateMotif': 1,
    'SectionalMotif': 1,
    'NVAR': 1,
    'Theta': 1,
    'ARDL': 1,
    # 'DynamicFactorMQ': 1,
}
best = [
    'LastValueNaive',
    'AverageValueNaive',
    'GLS',
    'GLM',
    'ETS',
    # 'ARIMA',
    'FBProphet',
    # 'RollingRegression',
    'GluonTS',
    'SeasonalNaive',
    'UnobservedComponents',
    # 'VARMAX',
    'VECM',
    # 'MotifSimulation',
    # 'UnivariateRegression',
    'MultivariateRegression',
    'WindowRegression',
    'VAR',
    'DatepartRegression',
    'UnivariateMotif',
    'MultivariateMotif',
    'NVAR',
    'SectionalMotif',
    'Theta',
    'ARDL',
]
# fastest models at any scale
superfast = [
    'ConstantNaive',
    'LastValueNaive',
    'AverageValueNaive',
    'GLS',
    'SeasonalNaive',
]
# relatively fast
fast = {
    'ConstantNaive': 1,
    'LastValueNaive': 1.5,
    'AverageValueNaive': 1,
    'GLS': 1,
    'SeasonalNaive': 1,
    'GLM': 1,
    'ETS': 1,
    # 'UnobservedComponents': 1,  # it's fast enough but I'll leave for parallel
    'VAR': 0.8,
    'VECM': 1,
    'WindowRegression': 0.5,  # this gets slow with Transformer, KerasRNN
    'DatepartRegression': 0.8,
    'UnivariateMotif': 1,
    'MultivariateMotif': 0.8,
    'SectionalMotif': 1,
    'NVAR': 1,
}
# models that can scale well if many CPU cores are available
parallel = {
    'ETS': 1,
    'FBProphet': 0.8,
    'ARIMA': 1,
    'GLM': 1,
    'UnobservedComponents': 1,
    "Greykite": 0.3,
    'UnivariateMotif': 1,
    'MultivariateMotif': 1,
    'Theta': 1,
    'ARDL': 1,
    'ARCH': 1,
}
# models that should be fast given many CPU cores
fast_parallel = {**parallel, **fast}
# models that are explicitly not production ready
experimental = [
    'MotifSimulation',
    'TensorflowSTS',
    'ComponentAnalysis',
    'TFPRegression',
]
# models that perform slowly at scale
slow = list((set(all_models) - set(fast.keys())) - set(experimental))
# use GPU
gpu = ['GluonTS', 'WindowRegression', 'PytorchForecasting']
# models with model-based upper/lower forecasts
probabilistic = [
    'ARIMA',
    'GluonTS',
    'FBProphet',
    'AverageValueNaive',
    'VARMAX',
    'DynamicFactor',
    'VAR',
    'UnivariateMotif',
    "MultivariateMotif",
    'SectionalMotif',
    'NVAR',
    'Theta',
    'ARDL',
    'UnobservedComponents',
    'DynamicFactorMQ',
    'PytorchForecasting',
    # 'MultivariateRegression',
    'ARCH',
]
# models that use the shared information of multiple series to improve accuracy
multivariate = [
    'VECM',
    'DynamicFactor',
    'GluonTS',
    'VARMAX',
    'RollingRegression',
    'WindowRegression',
    'VAR',
    "MultivariateMotif",
    'NVAR',
    'MultivariateRegression',
    'SectionalMotif',
    'DynamicFactorMQ',
    'PytorchForecasting',
]
univariate = list((set(all_models) - set(multivariate)) - set(experimental))
# USED IN AUTO_MODEL, models with no parameters
no_params = ['LastValueNaive', 'GLS']
# USED IN AUTO_MODEL, ONLY MODELS WHICH CAN ACCEPT RANDOM MIXING OF PARAMS
recombination_approved = [
    'SeasonalNaive',
    'MotifSimulation',
    "ETS",
    'DynamicFactor',
    'VECM',
    'VARMAX',
    'GLM',
    'ARIMA',
    'FBProphet',
    'GluonTS',
    'RollingRegression',
    'VAR',
    # 'WindowRegression',
    'TensorflowSTS',
    'TFPRegression',
    'UnivariateRegression',
    "Greykite",
    'UnivariateMotif',
    "MultivariateMotif",
    'NVAR',
    'MultivariateRegression',
    'SectionalMotif',
    'Theta',
    'ARDL',
    'NeuralProphet',
    'DynamicFactorMQ',
    'PytorchForecasting',
    'ARCH',
]
# USED IN AUTO_MODEL for models that don't share information among series
no_shared = [
    'ConstantNaive',
    'LastValueNaive',
    'AverageValueNaive',
    'GLM',
    'ETS',
    'ARIMA',
    'FBProphet',
    'SeasonalNaive',
    'UnobservedComponents',
    'TensorflowSTS',
    "GLS",
    "UnivariateRegression",
    "Greykite",
    'UnivariateMotif',
    'Theta',
    'ARDL',
    'NeuralProphet',
    'ARCH',
]
# allow the use of a regressor, need to accept "User" (fail if not given), have 'regressor' param method
regressor = [
    'GLM',
    'ARIMA',
    'FBProphet',
    'RollingRegression',
    'UnobservedComponents',
    'VECM',
    'DynamicFactor',
    'WindowRegression',
    'VAR',
    'DatepartRegression',
    "GluonTS",
    "UnivariateRegression",
    'MultivariateRegression',
    'SectionalMotif',  # kinda
    'ARDL',
    'NeuralProphet',
    'ARCH',
]
motifs = [
    'UnivariateMotif',
    "MultivariateMotif",
    'SectionalMotif',
    'MotifSimulation',
]
no_shared_fast = list(set(no_shared).intersection(set(fast_parallel)))
model_lists = {
    "all": all_models,
    "default": default,
    "fast": fast,
    "superfast": superfast,
    "parallel": parallel,
    "fast_parallel": fast_parallel,
    "probabilistic": probabilistic,
    "multivariate": multivariate,
    "univariate": univariate,
    "no_params": no_params,
    "recombination_approved": recombination_approved,
    "no_shared": no_shared,
    "no_shared_fast": no_shared_fast,
    "experimental": experimental,
    "slow": slow,
    "gpu": gpu,
    "regressor": regressor,
    "best": best,
    "motifs": motifs,
}


def auto_model_list(n_jobs, n_series, frequency):
    pass
