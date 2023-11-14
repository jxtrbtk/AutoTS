# -*- coding: utf-8 -*-
"""
Base model information

@author: Colin
"""
import json
import random
import warnings
import datetime
import numpy as np
import pandas as pd
from autots.tools.shaping import infer_frequency, clean_weights
from autots.evaluator.metrics import full_metric_evaluation


def create_forecast_index(frequency, forecast_length, train_last_date, last_date=None):
    if frequency == 'infer':
        raise ValueError(
            "create_forecast_index run without specific frequency, run basic_profile first or pass proper frequency to model init"
        )
    return pd.date_range(
        freq=frequency,
        start=train_last_date if last_date is None else last_date,
        periods=forecast_length + 1,
    )[
        1:
    ]  # note the disposal of the first (already extant) date


class ModelObject(object):
    """Generic class for holding forecasting models.

    Models should all have methods:
        .fit(df, future_regressor = []) (taking a DataFrame with DatetimeIndex and n columns of n timeseries)
        .predict(forecast_length = int, future_regressor = [], just_point_forecast = False)
        .get_new_params() - return a dictionary of weighted random selected parameters

    Args:
        name (str): Model Name
        frequency (str): String alias of datetime index frequency or else 'infer'
        prediction_interval (float): Confidence interval for probabilistic forecast
        n_jobs (int): used by some models that parallelize to multiple cores
    """

    def __init__(
        self,
        name: str = "Uninitiated Model Name",
        frequency: str = 'infer',
        prediction_interval: float = 0.9,
        regression_type: str = None,
        fit_runtime=datetime.timedelta(0),
        holiday_country: str = 'US',
        random_seed: int = 2020,
        verbose: int = 0,
        n_jobs: int = -1,
    ):
        self.name = name
        self.frequency = frequency
        self.prediction_interval = prediction_interval
        self.regression_type = regression_type
        self.fit_runtime = fit_runtime
        self.holiday_country = holiday_country
        self.random_seed = random_seed
        self.verbose = verbose
        self.verbose_bool = True if self.verbose > 1 else False
        self.n_jobs = n_jobs

    def __repr__(self):
        """Print."""
        return 'ModelObject of ' + self.name + ' uses standard .fit/.predict'

    def basic_profile(self, df):
        """Capture basic training details."""
        if 0 in df.shape:
            raise ValueError(f"{self.name} training dataframe has no data: {df.shape}")
        self.startTime = datetime.datetime.now()
        self.train_shape = df.shape
        self.column_names = df.columns
        self.train_last_date = df.index[-1]
        if self.frequency == 'infer':
            self.frequency = infer_frequency(df.index)

        return df

    def create_forecast_index(self, forecast_length: int, last_date=None):
        """Generate a pd.DatetimeIndex appropriate for a new forecast.

        Warnings:
            Requires ModelObject.basic_profile() being called as part of .fit()
        """

        return create_forecast_index(
            self.frequency, forecast_length, self.train_last_date, last_date
        )

    def get_params(self):
        """Return dict of current parameters."""
        return {}

    def get_new_params(self, method: str = 'random'):
        """Return dict of new parameters for parameter tuning."""
        return {}

    def fit_data(self, df, future_regressor=None):
        self.basic_profile(df)
        if future_regressor is not None:
            self.regressor_train = future_regressor
        return self

    @staticmethod
    def time():
        return datetime.datetime.now()


def apply_constraints(
    forecast,
    lower_forecast,
    upper_forecast,
    constraint_method,
    constraint_regularization,
    upper_constraint,
    lower_constraint,
    bounds,
    df_train=None,
):
    """Use constraint thresholds to adjust outputs by limit.
    Note that only one method of constraint can be used here, but if different methods are desired,
    this can be run twice, with None passed to the upper or lower constraint not being used.

    Args:
        forecast (pd.DataFrame): forecast df, wide style
        lower_forecast (pd.DataFrame): lower bound forecast df
            if bounds is False, upper and lower forecast dataframes are unused and can be empty
        upper_forecast (pd.DataFrame): upper bound forecast df
        constraint_method (str): one of
            stdev_min - threshold is min and max of historic data +/- constraint * st dev of data
            stdev - threshold is the mean of historic data +/- constraint * st dev of data
            absolute - input is array of length series containing the threshold's final value for each
            quantile - constraint is the quantile of historic data to use as threshold
        constraint_regularization (float): 0 to 1
            where 0 means no constraint, 1 is hard threshold cutoff, and in between is penalty term
        upper_constraint (float): or array, depending on method, None if unused
        lower_constraint (float): or array, depending on method, None if unused
        bounds (bool): if True, apply to upper/lower forecast, otherwise False applies only to forecast
        df_train (pd.DataFrame): required for quantile/stdev methods to find threshold values

    Returns:
        forecast, lower, upper (pd.DataFrame)
    """
    if constraint_method == "stdev_min":
        train_std = df_train.std(axis=0)
        if lower_constraint is not None:
            train_min = df_train.min(axis=0) - (lower_constraint * train_std)
        if upper_constraint is not None:
            train_max = df_train.max(axis=0) + (upper_constraint * train_std)
    elif constraint_method == "stdev":
        train_std = df_train.std(axis=0)
        train_mean = df_train.mean(axis=0)
        if lower_constraint is not None:
            train_min = train_mean - (lower_constraint * train_std)
        if upper_constraint is not None:
            train_max = train_mean + (upper_constraint * train_std)
    elif constraint_method == "absolute":
        train_min = lower_constraint
        train_max = upper_constraint
    elif constraint_method == "quantile":
        if lower_constraint is not None:
            train_min = df_train.quantile(lower_constraint, axis=0)
        if upper_constraint is not None:
            train_max = df_train.quantile(upper_constraint, axis=0)
    else:
        raise ValueError("constraint_method not recognized, adjust constraint")

    if constraint_regularization == 1:
        if lower_constraint is not None:
            forecast = forecast.clip(lower=train_min, axis=1)
        if upper_constraint is not None:
            forecast = forecast.clip(upper=train_max, axis=1)
        if bounds:
            if lower_constraint is not None:
                lower_forecast = lower_forecast.clip(lower=train_min, axis=1)
                upper_forecast = upper_forecast.clip(lower=train_min, axis=1)
            if upper_constraint is not None:
                lower_forecast = lower_forecast.clip(upper=train_max, axis=1)
                upper_forecast = upper_forecast.clip(upper=train_max, axis=1)
    else:
        if lower_constraint is not None:
            forecast.where(
                forecast >= train_min,
                forecast + (train_min - forecast) * constraint_regularization,
                inplace=True,
            )
        if upper_constraint is not None:
            forecast.where(
                forecast <= train_max,
                forecast + (train_max - forecast) * constraint_regularization,
                inplace=True,
            )
        if bounds:
            if lower_constraint is not None:
                lower_forecast.where(
                    lower_forecast >= train_min,
                    lower_forecast
                    + (train_min - lower_forecast) * constraint_regularization,
                    inplace=True,
                )
                upper_forecast.where(
                    upper_forecast >= train_min,
                    upper_forecast
                    + (train_min - upper_forecast) * constraint_regularization,
                    inplace=True,
                )
            if upper_constraint is not None:
                lower_forecast.where(
                    lower_forecast <= train_max,
                    lower_forecast
                    + (train_max - lower_forecast) * constraint_regularization,
                    inplace=True,
                )

                upper_forecast.where(
                    upper_forecast <= train_max,
                    upper_forecast
                    + (train_max - upper_forecast) * constraint_regularization,
                    inplace=True,
                )
    return forecast, lower_forecast, upper_forecast


def extract_single_series_from_horz(series, model_name, model_parameters):
    title_prelim = str(model_name)[0:80]
    if title_prelim == "Ensemble":
        ensemble_type = model_parameters.get('model_name', "Ensemble")
        # horizontal and mosaic ensembles
        if "series" in model_parameters.keys():
            model_id = model_parameters['series'].get(
                series, "Horizontal"
            )
            if isinstance(model_id, dict):
                model_id = list(model_id.values())
            if not isinstance(model_id, list):
                model_id = [str(model_id)]
            res = []
            for imod in model_id:
                res.append(
                    model_parameters.get("models", {})
                    .get(imod, {})
                    .get('Model', "Horizontal")
                )
            title_prelim = ", ".join(set(res))
            if len(model_id) > 1:
                title_prelim = "Mosaic: " + str(title_prelim)
        else:
            title_prelim = ensemble_type
    return str(title_prelim)


def extract_single_transformer(series, model_name, model_parameters, transformation_params):
    if model_name == "Ensemble":
        # horizontal and mosaic ensembles
        if "series" in model_parameters.keys():
            model_id = model_parameters['series'].get(
                series, "Horizontal"
            )
            if isinstance(model_id, dict):
                model_id = list(model_id.values())
            if not isinstance(model_id, list):
                model_id = [str(model_id)]
            res = []
            for imod in model_id:
                chosen_mod = model_parameters.get("models", {}).get(imod, {})
                res.append(
                    extract_single_transformer(
                        series, chosen_mod.get("Model"),
                        chosen_mod.get("ModelParameters"),
                        transformation_params=chosen_mod.get("TransformationParameters")
                    )
                )
            return ", ".join(res)
        allz = []
        for idz, mod in model_parameters.get("models").items():
            allz.append(
                extract_single_transformer(
                    series, mod.get("Model"),
                    mod.get("ModelParameters"),
                    transformation_params=mod.get("TransformationParameters")
                )
            )
        return ", ".join(allz)
    else:
        if isinstance(transformation_params, str):
            transformation_params = json.loads(transformation_params)
        trans_dict = transformation_params.get("transformations")
        if isinstance(trans_dict, dict):
            return ", ".join(list(trans_dict.values()))
        else:
            return "None"

def create_seaborn_palette_from_cmap(cmap_name="gist_rainbow", n=10):
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Get the colormap from matplotlib
    cm = plt.get_cmap(cmap_name)
    
    # Create a range of colors from the colormap
    colors = cm(np.linspace(0, 1, n))
    
    # Convert to a seaborn palette
    palette = sns.color_palette(colors)
    
    return palette

# Function to calculate the peak density of each model's distribution
def calculate_peak_density(model, data, group_col='Model', y_col='TotalRuntimeSeconds'):
    from scipy.stats import gaussian_kde

    model_data = data[data[group_col] == model][y_col]
    kde = gaussian_kde(model_data)
    return np.max(kde(model_data))

def plot_distributions(runtimes_data, group_col='Model', y_col='TotalRuntimeSeconds', xlim=None, xlim_right=None):
    import matplotlib.pyplot as plt
    import seaborn as sns

    single_obs_models = runtimes_data.groupby(group_col).filter(lambda x: len(x) == 1)
    multi_obs_models = runtimes_data.groupby(group_col).filter(lambda x: len(x) > 1)

    # Calculate the average peak density across all models with multiple observations
    average_peak_density = np.mean([calculate_peak_density(model, multi_obs_models, group_col, y_col) for model in multi_obs_models[group_col].unique()])

    # Correcting the color palette to match the number of unique models
    unique_models = runtimes_data[group_col].nunique()
    # palette = sns.color_palette("tab10", n_colors=unique_models)
    palette = create_seaborn_palette_from_cmap("gist_rainbow", n=unique_models)
    sorted_models = runtimes_data[group_col].value_counts().index.tolist()
    # sorted_models = runtimes_data[group_col].unique()
    zip_palette = dict(zip(sorted_models, palette))

    # Create a new figure for the plot
    fig = plt.figure(figsize=(12, 8))

    # Plot the density plots for multi-observation models
    density_plot = sns.kdeplot(  #noqa
        data=multi_obs_models, x=y_col, hue=group_col, fill=True,
        common_norm=False, palette=zip_palette, alpha=0.5
    )

    # Plot the points for single-observation models at the average peak density
    if not single_obs_models.empty:
        point_plot = sns.scatterplot(  #noqa
            data=single_obs_models, x=y_col,
            y=[average_peak_density]*len(single_obs_models),
            hue=group_col, palette=zip_palette, legend=False,
            marker='o', # s=10
        )
    # Adjusting legend - Manually combining elements
    handles, labels = [], []
    for model, color in zip_palette.items():
        handles.append(plt.Line2D([0], [0], linestyle="none", c=color, marker='o'))
        labels.append(model)

    # Create the combined legend
    plt.legend(handles, labels, title=group_col)  # , bbox_to_anchor=(1.05, 1), loc=2

    # Adding titles and labels
    plt.title(f'Distribution of {y_col} by {group_col}', fontsize=16)
    plt.xlabel(f'{y_col}', fontsize=14)
    plt.ylabel('Density', fontsize=14)

    # Adjust layout
    plt.tight_layout()
    if xlim is not None:
        plt.xlim(left=xlim)
    if xlim_right is not None:
        plt.xlim(right=runtimes_data[y_col].quantile(xlim_right))

    return fig


class PredictionObject(object):
    """Generic class for holding forecast information.

    Attributes:
        model_name
        model_parameters
        transformation_parameters
        forecast
        upper_forecast
        lower_forecast

    Methods:
        long_form_results: return complete results in long form
        total_runtime: return runtime for all model components in seconds
        plot
        evaluate
        apply_constraints
    """

    def __init__(
        self,
        model_name: str = 'Uninitiated',
        forecast_length: int = 0,
        forecast_index=np.nan,
        forecast_columns=np.nan,
        lower_forecast=np.nan,
        forecast=np.nan,
        upper_forecast=np.nan,
        prediction_interval: float = 0.9,
        predict_runtime=datetime.timedelta(0),
        fit_runtime=datetime.timedelta(0),
        model_parameters={},
        transformation_parameters={},
        transformation_runtime=datetime.timedelta(0),
        per_series_metrics=np.nan,
        per_timestamp=np.nan,
        avg_metrics=np.nan,
        avg_metrics_weighted=np.nan,
        full_mae_error=None,
        model=None,
        transformer=None,
    ):
        self.model_name = self.name = model_name
        self.model_parameters = model_parameters
        self.transformation_parameters = transformation_parameters
        self.forecast_length = forecast_length
        self.forecast_index = forecast_index
        self.forecast_columns = forecast_columns
        self.lower_forecast = lower_forecast
        self.forecast = forecast
        self.upper_forecast = upper_forecast
        self.prediction_interval = prediction_interval
        self.predict_runtime = predict_runtime
        self.fit_runtime = fit_runtime
        self.transformation_runtime = transformation_runtime
        # eval attributes
        self.per_series_metrics = per_series_metrics
        self.per_timestamp = per_timestamp
        self.avg_metrics = avg_metrics
        self.avg_metrics_weighted = avg_metrics_weighted
        self.full_mae_error = full_mae_error
        # model attributes, not normally used
        self.model = model
        self.transformer = transformer
        self.runtime_dict = None

    def __repr__(self):
        """Print."""
        if isinstance(self.forecast, pd.DataFrame):
            return "Prediction object: \nReturn .forecast, \n .upper_forecast, \n .lower_forecast \n .model_parameters \n .transformation_parameters"
        else:
            return "Empty prediction object."

    def __bool__(self):
        """bool version of class."""
        if isinstance(self.forecast, pd.DataFrame):
            return True
        else:
            return False

    def long_form_results(
        self,
        id_name="SeriesID",
        value_name="Value",
        interval_name='PredictionInterval',
        update_datetime_name=None,
    ):
        """Export forecasts (including upper and lower) as single 'long' format output

        Args:
            id_name (str): name of column containing ids
            value_name (str): name of column containing numeric values
            interval_name (str): name of column telling you what is upper/lower
            update_datetime_name (str): if not None, adds column with current timestamp and this name

        Returns:
            pd.DataFrame
        """
        try:
            upload = pd.melt(
                self.forecast,
                var_name=id_name,
                value_name=value_name,
                ignore_index=False,
            )
        except Exception:
            raise ImportError("Requires pandas>=1.1.0")
        upload[interval_name] = "50%"
        upload_upper = pd.melt(
            self.upper_forecast,
            var_name=id_name,
            value_name=value_name,
            ignore_index=False,
        )
        upload_upper[
            interval_name
        ] = f"{round(100 - ((1- self.prediction_interval)/2) * 100, 0)}%"
        upload_lower = pd.melt(
            self.lower_forecast,
            var_name=id_name,
            value_name=value_name,
            ignore_index=False,
        )
        upload_lower[
            interval_name
        ] = f"{round(((1- self.prediction_interval)/2) * 100, 0)}%"

        upload = pd.concat([upload, upload_upper, upload_lower], axis=0)
        if update_datetime_name is not None:
            upload[update_datetime_name] = datetime.datetime.utcnow()
        return upload

    def total_runtime(self):
        """Combine runtimes."""
        return self.fit_runtime + self.predict_runtime + self.transformation_runtime

    def extract_ensemble_runtimes(self):
        """Return a dataframe of final runtimes per model for standard ensembles."""
        if self.runtime_dict is None or not bool(self.model_parameters):
            return None
        else:
            runtimes = pd.DataFrame( self.runtime_dict.items(), columns=['ID', 'Runtime'])
            runtimes['TotalRuntimeSeconds'] = runtimes['Runtime'].dt.total_seconds()
            new_models = {x: y.get("Model") for x, y in self.model_parameters.get("models").items()}
            models = pd.DataFrame( new_models.items(), columns=['ID', 'Model'])
            return runtimes.merge(models, how='left', on='ID')

    def plot_ensemble_runtimes(self, xlim_right=None):
        """Plot ensemble runtimes by model type."""
        runtimes_data = self.extract_ensemble_runtimes()

        if runtimes_data is None:
            return None
        else:
            return plot_distributions(
                runtimes_data, group_col='Model', y_col='TotalRuntimeSeconds',
                xlim=0, xlim_right=xlim_right,
            )

    def plot_df(
        self,
        df_wide=None,
        series: str = None,
        remove_zeroes: bool = False,
        interpolate: str = None,
        start_date: str = None,
    ):
        if series is None:
            series = random.choice(self.forecast.columns)

        model_name = self.model_name
        if model_name == "Ensemble":
            if 'series' in self.model_parameters.keys():
                h_params = self.model_parameters['series'][series]
                if isinstance(h_params, str):
                    model_name = self.model_parameters['models'][h_params]['Model']

        if df_wide is not None:
            plot_df = pd.DataFrame(
                {
                    'actuals': df_wide[series],
                    'up_forecast': self.upper_forecast[series],
                    'low_forecast': self.lower_forecast[series],
                    'forecast': self.forecast[series],
                }
            )
        else:
            plot_df = pd.DataFrame(
                {
                    'up_forecast': self.upper_forecast[series],
                    'low_forecast': self.lower_forecast[series],
                    'forecast': self.forecast[series],
                }
            )
        if remove_zeroes:
            plot_df[plot_df == 0] = np.nan
        if interpolate is not None:
            plot_df["actuals"] = plot_df["actuals"].interpolate(
                method=interpolate, limit_direction="backward"
            )
            plot_df["forecast"] = plot_df["forecast"].interpolate(
                method=interpolate, limit_direction="backward", limit=5
            )

        if start_date is not None:
            start_date = pd.to_datetime(start_date)
            if plot_df.index.max() < start_date:
                raise ValueError("start_date is more recent than all data provided")
            plot_df = plot_df[plot_df.index >= start_date]
        return plot_df

    def plot(
        self,
        df_wide=None,
        series: str = None,
        remove_zeroes: bool = False,
        interpolate: str = None,
        start_date: str = "auto",
        alpha=0.3,
        facecolor="black",
        loc="upper right",
        title=None,
        title_substring=None,
        vline=None,
        colors=None,
        include_bounds=True,
        **kwargs,
    ):
        """Generate an example plot of one series. Does not handle non-numeric forecasts.

        Args:
            df_wide (str): historic data for plotting actuals
            series (str): column name of series to plot. Random if None.
            ax: matplotlib axes to pass through to pd.plot()
            remove_zeroes (bool): if True, don't plot any zeroes
            interpolate (str): if not None, a method to pass to pandas interpolate
            start_date (str): Y-m-d string or Timestamp to remove all data before
            vline (datetime): datetime of dashed vertical line to plot
            colors (dict): colors mapping dictionary col: color
            alpha (float): intensity of bound interval shading
            title (str): title
            title_substring (str): additional title details to pass to existing, moves series name to axis
            include_bounds (bool): if True, shows region of upper and lower forecasts
            **kwargs passed to pd.DataFrame.plot()
        """
        if start_date == "auto":
            if df_wide is not None:
                slx = -self.forecast_length * 3
                if abs(slx) > df_wide.shape[0]:
                    slx = 0
                start_date = df_wide.index[slx]
            else:
                start_date = self.forecast.index[0]

        if series is None:
            series = random.choice(self.forecast.columns)
        plot_df = self.plot_df(
            df_wide=df_wide,
            series=series,
            remove_zeroes=remove_zeroes,
            interpolate=interpolate,
            start_date=start_date,
        )
        if self.forecast_length == 1 and 'actuals' in plot_df.columns:
            if plot_df.shape[0] > 3:
                plot_df['forecast'].iloc[-2] = plot_df['actuals'].iloc[-2]
        if 'actuals' not in plot_df.columns:
            plot_df['actuals'] = np.nan
        if colors is None:
            colors = {
                'low_forecast': '#A5ADAF',
                'up_forecast': '#A5ADAF',
                'forecast': '#003399',  # '#4D4DFF',
                'actuals': '#AFDBF5',
            }
        if title is None:
            title_prelim = extract_single_series_from_horz(
                series, model_name=self.model_name, model_parameters=self.model_parameters
            )[0: 80]
            if title_substring is None:
                title = f"{series} with model {title_prelim}"
            else:
                title = f"{title_substring} with model {title_prelim}"

        ax = plot_df[['actuals', 'forecast']].plot(title=title, color=colors, **kwargs)
        if include_bounds:
            ax.fill_between(
                plot_df.index,
                plot_df['up_forecast'],
                plot_df['low_forecast'],
                alpha=alpha,
                color="#A5ADAF",
                label="Prediction Interval",
            )
        if vline is not None:
            ax.vlines(
                x=vline,
                ls='--',
                lw=1,
                colors='darkred',
                ymin=plot_df.min().min(),
                ymax=plot_df.max().max(),
            )
            # ax.text(vline, plot_df.max().max(), "Event", color='darkred', verticalalignment='top')
        if title_substring is not None:
            ax.set_ylabel(series)
        # ax.grid(True, which="both", ls="--", linewidth=0.5)
        # ax.legend(loc=loc)
        return ax

    def plot_grid(
        self,
        df_wide=None,
        start_date='auto',
        interpolate=None,
        remove_zeroes=False,
        figsize=(24, 18),
        title="AutoTS Forecasts",
        cols=None,
        colors=None,
        include_bounds=True,
    ):
        """Plots multiple series in a grid, if present. Mostly identical args to the single plot function."""
        import matplotlib.pyplot as plt

        if cols is None:
            cols = self.forecast_columns
        num_cols = len(cols)
        if num_cols > 4:
            nrow = 2
            ncol = 3
        elif num_cols > 2:
            nrow = 2
            ncol = 2
        else:
            nrow = 1
            ncol = 2
        fig, axes = plt.subplots(nrow, ncol, figsize=figsize, constrained_layout=True)
        fig.suptitle(title, fontsize='xx-large')
        count = 0
        for r in range(nrow):
            for c in range(ncol):
                if nrow > 1:
                    ax = axes[r, c]
                else:
                    ax = axes[c]
                if count + 1 > num_cols:
                    pass
                else:
                    col = cols[count]
                    self.plot(
                        df_wide=df_wide,
                        series=col,
                        remove_zeroes=remove_zeroes,
                        interpolate=interpolate,
                        start_date=start_date,
                        colors=colors,
                        include_bounds=include_bounds,
                        ax=ax,
                    )
                    count += 1
        return fig

    def evaluate(
        self,
        actual,
        series_weights: dict = None,
        df_train=None,
        per_timestamp_errors: bool = False,
        full_mae_error: bool = True,
        scaler=None,
        cumsum_A=None,
        diff_A=None,
        last_of_array=None,
    ):
        """Evalute prediction against test actual. Fills out attributes of base object.

        This fails with pd.NA values supplied.

        Args:
            actual (pd.DataFrame): dataframe of actual values of (forecast length * n series)
            series_weights (dict): key = column/series_id, value = weight
            df_train (pd.DataFrame): historical values of series, wide,
                used for setting scaler for SPL
                necessary for MADE and Contour if forecast_length == 1
                if None, actuals are used instead (suboptimal).
            per_timestamp (bool): whether to calculate and return per timestamp direction errors

        Returns:
            per_series_metrics (pandas.DataFrame): contains a column for each series containing accuracy metrics
            per_timestamp (pandas.DataFrame): smape accuracy for each timestamp, avg of all series
            avg_metrics (pandas.Series): average values of accuracy across all input series
            avg_metrics_weighted (pandas.Series): average values of accuracy across all input series weighted by series_weight, if given
            full_mae_errors (numpy.array): abs(actual - forecast)
            scaler (numpy.array): precomputed scaler for efficiency, avg value of series in order of columns
        """
        # arrays are faster for math than pandas dataframes
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            (
                self.per_series_metrics,
                self.full_mae_errors,
                self.squared_errors,
                self.upper_pl,
                self.lower_pl,
            ) = full_metric_evaluation(
                A=actual,
                F=self.forecast,
                upper_forecast=self.upper_forecast,
                lower_forecast=self.lower_forecast,
                df_train=df_train,
                prediction_interval=self.prediction_interval,
                columns=self.forecast.columns,
                scaler=scaler,
                return_components=True,
                cumsum_A=cumsum_A,
                diff_A=diff_A,
                last_of_array=last_of_array,
            )

        if per_timestamp_errors:
            smape_df = abs(self.forecast - actual) / (abs(self.forecast) + abs(actual))
            weight_mean = np.mean(list(series_weights.values()))
            wsmape_df = (smape_df * series_weights) / weight_mean
            smape_cons = (np.nansum(wsmape_df, axis=1) * 200) / np.count_nonzero(
                ~np.isnan(actual), axis=1
            )
            per_timestamp = pd.DataFrame({'weighted_smape': smape_cons}).transpose()
            self.per_timestamp = per_timestamp

        # check series_weights information
        if series_weights is None:
            series_weights = clean_weights(weights=False, series=self.forecast.columns)
        # make sure the series_weights are passed correctly to metrics
        if len(series_weights) != self.forecast.shape[1]:
            series_weights = {col: series_weights[col] for col in self.forecast.columns}

        # this weighting won't work well if entire metrics are NaN
        # but results should still be comparable
        self.avg_metrics_weighted = (self.per_series_metrics * series_weights).sum(
            axis=1, skipna=True
        ) / sum(series_weights.values())
        self.avg_metrics = self.per_series_metrics.mean(axis=1, skipna=True)
        return self

    def apply_constraints(
        self,
        constraint_method="quantile",
        constraint_regularization=0.5,
        upper_constraint=1.0,
        lower_constraint=0.0,
        bounds=True,
        df_train=None,
    ):
        """Use constraint thresholds to adjust outputs by limit.
        Note that only one method of constraint can be used here, but if different methods are desired,
        this can be run twice, with None passed to the upper or lower constraint not being used.

        Args:
            constraint_method (str): one of
                stdev_min - threshold is min and max of historic data +/- constraint * st dev of data
                stdev - threshold is the mean of historic data +/- constraint * st dev of data
                absolute - input is array of length series containing the threshold's final value for each
                quantile - constraint is the quantile of historic data to use as threshold
            constraint_regularization (float): 0 to 1
                where 0 means no constraint, 1 is hard threshold cutoff, and in between is penalty term
            upper_constraint (float): or array, depending on method, None if unused
            lower_constraint (float): or array, depending on method, None if unused
            bounds (bool): if True, apply to upper/lower forecast, otherwise False applies only to forecast
            df_train (pd.DataFrame): required for quantile/stdev methods to find threshold values

        Returns:
            self
        """
        self.forecast, self.lower_forecast, self.upper_forecast = apply_constraints(
            self.forecast,
            self.lower_forecast,
            self.upper_forecast,
            constraint_method,
            constraint_regularization,
            upper_constraint,
            lower_constraint,
            bounds,
            df_train,
        )
        return self
