# -*- coding: utf-8 -*-
"""
seasonal

@author: Colin
"""
import random
import numpy as np
import pandas as pd
from autots.tools.lunar import moon_phase
from autots.tools.window_functions import sliding_window_view
from autots.tools.holiday import holiday_flag


def seasonal_int(include_one: bool = False, small=False, very_small=False):
    """Generate a random integer of typical seasonalities.

    Args:
        include_one (bool): whether to include 1 in output options
        small (bool): if True, keep below 364
        very_small (bool): if True keep below 30
    """
    prob_dict = {
        -1: 0.1,  # random int
        1: 0.05,  # previous day
        2: 0.1,
        4: 0.05,  # quarters
        7: 0.15,  # week
        10: 0.01,
        12: 0.1,  # months
        24: 0.1,  # months or hours
        28: 0.1,  # days in month to weekday
        60: 0.05,
        96: 0.04,  # quarter in days
        168: 0.01,
        364: 0.1,  # year to weekday
        1440: 0.01,
        420: 0.01,
        52: 0.01,
        84: 0.01,
    }
    lag = random.choices(
        list(prob_dict.keys()),
        list(prob_dict.values()),
        k=1,
    )[0]
    if lag == -1:
        lag = random.randint(2, 100)
    if not include_one and lag == 1:
        lag = seasonal_int(include_one=include_one, small=small, very_small=very_small)
    if small:
        lag = lag if lag < 364 else 364
    if very_small:
        while lag > 30:
            lag = seasonal_int(include_one=include_one, very_small=very_small)
    return int(lag)


date_part_methods = [
    "recurring",
    "simple",
    "expanded",
    "simple_2",
    "simple_3",
    'lunar_phase',
    "simple_binarized",
    "simple_binarized_poly",
    "expanded_binarized",
    'common_fourier',
    'common_fourier_rw',
]

origin_ts = "2030-01-01"


def date_part(
    DTindex,
    method: str = 'simple',
    set_index: bool = True,
    polynomial_degree: int = None,
    holiday_country: str = None,
    holiday_countries_used: bool = True,
):
    """Create date part columns from pd.DatetimeIndex.

    Args:
        DTindex (pd.DatetimeIndex): datetime index to provide dates
        method (str): expanded, recurring, or simple
            simple - just day, year, month, weekday
            expanded - all available futures
            recurring - all features that should commonly repeat without aging
            simple_2
            simple_3
            simple_binarized
            expanded_binarized
            common_fourier
        set_index (bool): if True, return DTindex as index of df
        polynomial_degree (int): add this degree of sklearn polynomial features if not None

    Returns:
        pd.Dataframe with DTindex
    """
    # recursive
    if isinstance(method, list):
        all_seas = []
        for seas in method:
            all_seas.append(date_part(DTindex, method=seas, set_index=True))
        date_part_df = pd.concat(all_seas, axis=1)
    elif "_poly" in str(method):
        method = method.replace("_poly", "")
        polynomial_degree = 2

    if isinstance(method, (int, float)):
        date_part_df = fourier_df(DTindex, seasonality=method, order=6)
    elif isinstance(method, list):
        # remove duplicate columns if present
        date_part_df = date_part_df.loc[:, ~date_part_df.columns.duplicated()]
    elif method in datepart_components:
        date_part_df = create_datepart_components(DTindex, method)
    elif method == 'recurring':
        date_part_df = pd.DataFrame(
            {
                'month': DTindex.month,
                'day': DTindex.day,
                'weekday': DTindex.weekday,
                'weekend': (DTindex.weekday > 4).astype(int),
                'hour': DTindex.hour,
                'quarter': DTindex.quarter,
                'midyear': (
                    (DTindex.dayofyear > 74) & (DTindex.dayofyear < 258)
                ).astype(
                    int
                ),  # 2 season
            }
        )
    elif method in ["simple_2", "simple_2_poly"]:
        date_part_df = pd.DataFrame(
            {
                'month': DTindex.month,
                'day': DTindex.day,
                'weekday': DTindex.weekday,
                'weekend': (DTindex.weekday > 4).astype(int),
                'epoch': pd.to_numeric(
                    DTindex, errors='coerce', downcast='integer'
                ).values
                / 100000000000,
            }
        )
    elif method in ["simple_3", "lunar_phase"]:
        # trying to *prevent* it from learning holidays for this one
        date_part_df = pd.DataFrame(
            {
                'month': pd.Categorical(
                    DTindex.month, categories=list(range(1, 13)), ordered=True
                ),
                'weekday': pd.Categorical(
                    DTindex.weekday, categories=list(range(7)), ordered=True
                ),
                'weekend': (DTindex.weekday > 4).astype(int),
                'quarter': DTindex.quarter,
                'epoch': DTindex.to_julian_date(),
            }
        )
        # date_part_df['weekday'] = date_part_df['month'].astype(pd.CategoricalDtype(categories=list(range(6))))
        date_part_df = pd.get_dummies(
            date_part_df, columns=['month', 'weekday'], dtype=float
        )
        if method == "lunar_phase":
            date_part_df['phase'] = moon_phase(DTindex)
    elif "simple_binarized" in method:
        date_part_df = pd.DataFrame(
            {
                'month': pd.Categorical(
                    DTindex.month, categories=list(range(1, 13)), ordered=True
                ),
                'weekday': pd.Categorical(
                    DTindex.weekday, categories=list(range(7)), ordered=True
                ),
                'day': DTindex.day,
                'weekend': (DTindex.weekday > 4).astype(int),
                'epoch': DTindex.to_julian_date(),
            }
        )
        date_part_df = pd.get_dummies(
            date_part_df, columns=['month', 'weekday'], dtype=float
        )
    elif method in "expanded_binarized":
        date_part_df = pd.DataFrame(
            {
                'month': pd.Categorical(
                    DTindex.month, categories=list(range(1, 13)), ordered=True
                ),
                'weekday': pd.Categorical(
                    DTindex.weekday, categories=list(range(7)), ordered=True
                ),
                'day': pd.Categorical(
                    DTindex.day, categories=list(range(1, 32)), ordered=True
                ),
                'weekdayofmonth': pd.Categorical(
                    (DTindex.day - 1) // 7 + 1,
                    categories=list(range(1, 6)),
                    ordered=True,
                ),
                'weekend': (DTindex.weekday > 4).astype(int),
                'quarter': DTindex.quarter,
                'epoch': DTindex.to_julian_date(),
            }
        )
        date_part_df = pd.get_dummies(
            date_part_df,
            columns=['month', 'weekday', 'day', 'weekdayofmonth'],
            dtype=float,
        )
    elif method in ["common_fourier", "common_fourier_rw"]:
        seasonal_list = []
        DTmin = DTindex.min()
        DTmax = DTindex.max()
        # 1 time step will always not work with this
        # for new seasonal_ratio, worse case scenario is 2 steps ahead so one season / 2
        # in order to assure error on wrong seasonality choice in train vs test, we must have different sum orders for each seasonality
        if len(DTindex) <= 1:
            seasonal_ratio = 1  # assume daily, but weekly or monthly seems more likely for 1 step forecasts
        else:
            seasonal_ratio = ((DTmax - DTmin).days + 1) / len(DTindex)
        # seasonal_ratio = (DTmax.year - DTmin.year + 1) / len(DTindex)  # old ratio
        # hourly
        # if seasonal_ratio < 0.001:  # 0.00011 to 0.00023
        if seasonal_ratio < 0.75:  # 0.00011 to 0.00023
            t = DTindex - pd.Timestamp(origin_ts)
            t = (t.days * 24) + (t.components['minutes'] / 60)
            # add hourly, weekly, yearly
            seasonal_list.append(fourier_series(t, p=8766, n=10))
            seasonal_list.append(fourier_series(t, p=24, n=3))
            seasonal_list.append(fourier_series(t, p=168, n=5))
            # interactions
            seasonal_list.append(
                fourier_series(t, p=168, n=5) * fourier_series(t, p=24, n=5)
            )
            seasonal_list.append(
                fourier_series(t, p=168, n=3) * fourier_series(t, p=8766, n=3)
            )
        # daily (+ business day)
        # elif seasonal_ratio < 0.012:  # 0.0027 to 0.0055
        elif seasonal_ratio < 3.5:  # 0.0027 to 0.0055
            t = (DTindex - pd.Timestamp(origin_ts)).days
            # add yearly and weekly seasonality
            seasonal_list.append(fourier_series(t, p=365.25, n=10))
            seasonal_list.append(fourier_series(t, p=7, n=3))
            # interaction
            seasonal_list.append(
                fourier_series(t, p=7, n=5) * fourier_series(t, p=365.25, n=5)
            )
        # weekly
        # elif seasonal_ratio < 0.05:  # 0.019 to 0.038
        elif seasonal_ratio < 12:  # 0.019 to 0.038
            t = (DTindex - pd.Timestamp(origin_ts)).days
            seasonal_list.append(fourier_series(t, p=365.25, n=10))
            seasonal_list.append(fourier_series(t, p=28, n=4))
        # monthly
        # elif seasonal_ratio < 0.5:  # 0.083 to 0.154
        elif seasonal_ratio < 182:  # 0.083 to 0.154
            t = (DTindex - pd.Timestamp(origin_ts)).days
            seasonal_list.append(fourier_series(t, p=365.25, n=3))
            seasonal_list.append(fourier_series(t, p=1461, n=10))
        # yearly
        else:
            t = (DTindex - pd.Timestamp(origin_ts)).days
            seasonal_list.append(fourier_series(t, p=1461, n=10))
        date_part_df = (
            pd.DataFrame(np.concatenate(seasonal_list, axis=1))
            .rename(columns=lambda x: "seasonalitycommonfourier_" + str(x))
            .round(6)
        )
        if method == "common_fourier_rw":
            date_part_df['epoch'] = (DTindex.to_julian_date() ** 0.65).astype(int)
    else:
        # method == "simple"
        date_part_df = pd.DataFrame(
            {
                'year': DTindex.year,
                'month': DTindex.month,
                'day': DTindex.day,
                'weekday': DTindex.weekday,
            }
        )
        if method == 'expanded':
            try:
                weekyear = DTindex.isocalendar().week.to_numpy()
            except Exception:
                weekyear = DTindex.week
            date_part_df2 = pd.DataFrame(
                {
                    'hour': DTindex.hour,
                    'week': weekyear,
                    'quarter': DTindex.quarter,
                    'dayofyear': DTindex.dayofyear,
                    'midyear': (
                        (DTindex.dayofyear > 74) & (DTindex.dayofyear < 258)
                    ).astype(
                        int
                    ),  # 2 season
                    'weekend': (DTindex.weekday > 4).astype(int),
                    'weekdayofmonth': (DTindex.day - 1) // 7 + 1,
                    'month_end': (DTindex.is_month_end).astype(int),
                    'month_start': (DTindex.is_month_start).astype(int),
                    "quarter_end": (DTindex.is_quarter_end).astype(int),
                    'year_end': (DTindex.is_year_end).astype(int),
                    'daysinmonth': DTindex.daysinmonth,
                    'epoch': pd.to_numeric(
                        DTindex, errors='coerce', downcast='integer'
                    ).values
                    - 946684800000000000,
                    'us_election_year': (DTindex.year % 4 == 0).astype(
                        int
                    ),  # also Olympics
                }
            )
            date_part_df = pd.concat([date_part_df, date_part_df2], axis=1)

    if polynomial_degree is not None:
        from sklearn.preprocessing import PolynomialFeatures

        date_part_df = pd.DataFrame(
            PolynomialFeatures(polynomial_degree, include_bias=False).fit_transform(
                date_part_df
            )
        )
        date_part_df.columns = ['dp' + str(x) for x in date_part_df.columns]
    if isinstance(date_part_df, pd.Index):
        date_part_df = pd.Series(date_part_df)
    if set_index:
        date_part_df.index = DTindex
    if holiday_country is not None and holiday_countries_used:
        date_part_df = pd.concat(
            [
                date_part_df,
                holiday_flag(
                    DTindex, country=holiday_country, encode_holiday_type=True
                ),
            ],
            axis=1,
            ignore_index=not set_index,
        )
    return date_part_df


def fourier_series(t, p=365.25, n=10):
    # 2 pi n / p
    x = 2 * np.pi * np.arange(1, n + 1) / p
    # 2 pi n / p * t
    x = x * np.asarray(t)[:, None]
    x = np.concatenate((np.cos(x), np.sin(x)), axis=1)
    return x


def fourier_df(DTindex, seasonality, order=10, t=None, history_days=None):
    if history_days is None:
        history_days = (DTindex.max() - DTindex.min()).days
    if t is None:
        t = (DTindex - pd.Timestamp(origin_ts)).days
    return pd.DataFrame(
        fourier_series(np.asarray(t), seasonality / history_days, n=order)
    ).rename(columns=lambda x: f"seasonality{seasonality}_" + str(x))


datepart_components = [
    "dayofweek",
    "month",
    'day',
    "weekend",
    "weekdayofmonth",
    "hour",
    "daysinmonth",
    "quarter",
    "dayofyear",
    "weekdaymonthofyear",
    "dayofmonthofyear",
    "is_month_end",
    "is_month_start",
    "is_quarter_start",
    "is_quarter_end",
    "days_from_epoch",
]


def create_datepart_components(DTindex, seasonality):
    """single date part one-hot flags."""
    if seasonality == "dayofweek":
        return pd.get_dummies(
            pd.Categorical(DTindex.weekday, categories=list(range(7)), ordered=True),
            dtype=np.uint8,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    elif seasonality == "month":
        return pd.get_dummies(
            pd.Categorical(DTindex.month, categories=list(range(1, 13)), ordered=True),
            dtype=np.uint8,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    elif seasonality == "day":
        return pd.get_dummies(
            pd.Categorical(DTindex.day, categories=list(range(1, 32)), ordered=True),
            dtype=np.uint8,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    elif seasonality == "weekend":
        return pd.DataFrame((DTindex.weekday > 4).astype(int), columns=["weekend"])
    elif seasonality == "weekdayofmonth":
        return pd.get_dummies(
            pd.Categorical(
                (DTindex.day - 1) // 7 + 1,
                categories=list(range(1, 6)),
                ordered=True,
            ),
            dtype=float,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    # recommend used in combination with some combination like dayofweek and quarter
    elif seasonality == "weekdaymonthofyear":
        monweek = (
            ((DTindex.day - 1) // 7 + 1).astype(str) + (DTindex.weekday).astype(str)
        ).astype(int)
        # because not much data for last week (week 5) of months unless many years of data
        monweek = monweek.where(monweek <= 50, 50)
        strs = DTindex.month.astype(str) + monweek.astype(str)
        cat_index = pd.date_range(
            "2020-01-01", "2021-01-01", freq='D'
        )  # must be a leap year
        catweek = (
            ((cat_index.day - 1) // 7 + 1).astype(str) + (cat_index.weekday).astype(str)
        ).astype(int)
        catweek = catweek.where(catweek <= 50, 50)
        cats = (cat_index.month.astype(str) + catweek.astype(str)).unique()
        return pd.get_dummies(
            pd.Categorical(
                strs,
                categories=cats,
                ordered=False,
            ),
            dtype=float,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    elif seasonality == "dayofmonthofyear":
        strs = DTindex.month.astype(str) + DTindex.day.astype(str)
        cat_index = pd.date_range(
            "2020-01-01", "2021-01-01", freq='D'
        )  # must be a leap yaer
        cats = (cat_index.month.astype(str) + cat_index.day.astype(str)).unique()
        return pd.get_dummies(
            pd.Categorical(
                strs,
                categories=cats,
                ordered=False,
            ),
            dtype=float,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    elif seasonality == "hour":
        return pd.get_dummies(
            pd.Categorical(DTindex.hour, categories=list(range(1, 25)), ordered=True),
            dtype=np.uint8,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    elif seasonality == "daysinmonth":
        return pd.DataFrame({'daysinmonth': DTindex.daysinmonth})
    elif seasonality == "quarter":
        return pd.get_dummies(
            pd.Categorical(DTindex.quarter, categories=list(range(1, 5)), ordered=True),
            dtype=np.uint8,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    elif seasonality == "dayofyear":
        return pd.get_dummies(
            pd.Categorical(
                DTindex.dayofyear, categories=list(range(1, 367)), ordered=True
            ),
            dtype=np.uint16,
        ).rename(columns=lambda x: f"{seasonality}_" + str(x))
    elif seasonality == "is_month_end":
        return pd.DataFrame({'is_month_end': DTindex.is_month_end})
    elif seasonality == "is_month_start":
        return pd.DataFrame({'is_month_start': DTindex.is_month_start})
    elif seasonality == "is_quarter_start":
        return pd.DataFrame({'is_quarter_start': DTindex.is_quarter_start})
    elif seasonality == "is_quarter_end":
        return pd.DataFrame({'is_quarter_end': DTindex.is_quarter_end})
    elif seasonality == "days_from_epoch":
        return (DTindex - pd.Timestamp('2000-01-01')).days.astype('int32')
    else:
        raise ValueError(
            f"create_datepart_components `{seasonality}` is not recognized"
        )


def create_seasonality_feature(DTindex, t, seasonality, history_days=None):
    """Cassandra-designed feature generator."""
    # for consistency, all must have a range index, not date index
    # fourier orders
    if isinstance(seasonality, (int, float)):
        return fourier_df(
            DTindex, seasonality=seasonality, t=t, history_days=history_days
        )
    # dateparts
    elif seasonality in datepart_components:
        return create_datepart_components(DTindex, seasonality)
    elif seasonality in date_part_methods:
        return date_part(DTindex, method=seasonality, set_index=False)
    else:
        return ValueError(
            f"Seasonality `{seasonality}` not recognized. Must be int, float, or a select type string such as 'dayofweek'"
        )


def random_datepart(method='random'):
    """New random parameters for seasonality."""
    seasonalities = random.choices(
        [
            "recurring",
            "simple",
            "expanded",
            "simple_2",
            "simple_binarized",
            "expanded_binarized",
            'common_fourier',
            'common_fourier_rw',
            "simple_poly",
            [7, 365.25],
            ["dayofweek", 365.25],
            ['weekdayofmonth', 'common_fourier'],
            "other",
        ],
        [0.4, 0.3, 0.3, 0.3, 0.4, 0.35, 0.45, 0.2, 0.1, 0.1, 0.05, 0.1, 0.2],
    )[0]
    if seasonalities == "other":
        predefined = random.choices([True, False], [0.5, 0.5])[0]
        if predefined:
            seasonalities = [random.choice(date_part_methods)]
        else:
            comp_opts = datepart_components + [7, 365.25, 12]
            seasonalities = random.choices(comp_opts, k=2)
    return seasonalities


def seasonal_window_match(
    DTindex,
    k,
    window_size,
    forecast_length,
    datepart_method,
    distance_metric,
    full_sort=False,
):
    array = date_part(DTindex, method=datepart_method).to_numpy()

    # when k is larger, can be more aggressive on allowing a longer portion into view
    min_k = 5
    if k > min_k:
        n_tail = min(window_size, forecast_length)
    else:
        n_tail = forecast_length
    # finding sliding windows to compare
    temp = sliding_window_view(array[:-n_tail, :], window_size, axis=0)
    # compare windows by metrics
    last_window = array[-window_size:, :]
    if distance_metric == "mae":
        scores = np.mean(np.abs(temp - last_window.T), axis=2)
    elif distance_metric == "canberra":
        divisor = np.abs(temp) + np.abs(last_window.T)
        divisor[divisor == 0] = 1
        scores = np.mean(np.abs(temp - last_window.T) / divisor, axis=2)
    elif distance_metric == "minkowski":
        p = 2
        scores = np.sum(np.abs(temp - last_window.T) ** p, axis=2) ** (1 / p)
    elif distance_metric == "euclidean":
        scores = np.sqrt(np.sum((temp - last_window.T) ** 2, axis=2))
    elif distance_metric == "chebyshev":
        scores = np.max(np.abs(temp - last_window.T), axis=2)
    elif distance_metric == "mqae":
        q = 0.85
        ae = np.abs(temp - last_window.T)
        if ae.shape[2] <= 1:
            vals = ae
        else:
            qi = int(ae.shape[2] * q)
            qi = qi if qi > 1 else 1
            vals = np.partition(ae, qi, axis=2)[..., :qi]
        scores = np.mean(vals, axis=2)
    elif distance_metric == "mse":
        scores = np.mean((temp - last_window.T) ** 2, axis=2)
    else:
        raise ValueError(f"distance_metric: {distance_metric} not recognized")

    # select smallest windows
    if full_sort:
        min_idx = np.argsort(scores.mean(axis=1), axis=0)[:k]
    else:
        min_idx = np.argpartition(scores.mean(axis=1), k - 1, axis=0)[:k]
    # take the period starting AFTER the window
    test = (
        np.broadcast_to(
            np.arange(0, forecast_length)[..., None],
            (forecast_length, min_idx.shape[0]),
        )
        + min_idx
        + window_size
    )
    # for data over the end, fill last value
    if k > min_k:
        test = np.where(test >= len(DTindex), -1, test)
    return test, scores


def seasonal_independent_match(
    DTindex,
    DTindex_future,
    k,
    datepart_method='simple_binarized',
    distance_metric='canberra',
    full_sort=False,
    nan_array=None,
):
    array = date_part(DTindex, method=datepart_method)
    if nan_array is not None:
        array[nan_array] = np.inf
    future_array = date_part(DTindex_future, method=datepart_method).to_numpy()

    # when k is larger, can be more aggressive on allowing a longer portion into view
    min_k = 5
    # compare windows by metrics
    a = array.to_numpy()[:, None]
    b = future_array
    if distance_metric == "mae":
        scores = np.mean(np.abs(a - b), axis=2)
    elif distance_metric == "canberra":
        divisor = np.abs(a) + np.abs(b)
        divisor[divisor == 0] = 1
        scores = np.mean(np.abs(a - b) / divisor, axis=2)
    elif distance_metric == "minkowski":
        p = 2
        scores = np.sum(np.abs(a - b) ** p, axis=2) ** (1 / p)
    elif distance_metric == "euclidean":
        scores = np.sqrt(np.sum((a - b) ** 2, axis=2))
    elif distance_metric == "chebyshev":
        scores = np.max(np.abs(a - b), axis=2)
    elif distance_metric == "mqae":
        q = 0.85
        ae = np.abs(a - b)
        if ae.shape[2] <= 1:
            vals = ae
        else:
            qi = int(ae.shape[2] * q)
            qi = qi if qi > 1 else 1
            vals = np.partition(ae, qi, axis=2)[..., :qi]
        scores = np.mean(vals, axis=2)
    elif distance_metric == "mse":
        scores = np.mean((a - b) ** 2, axis=2)
    else:
        raise ValueError(f"distance_metric: {distance_metric} not recognized")

    # select smallest windows
    if full_sort:
        min_idx = np.argsort(scores, axis=0)[:k]
    else:
        min_idx = np.argpartition(scores, k - 1, axis=0)[:k]
    # take the period starting AFTER the window
    test = min_idx.T
    # for data over the end, fill last value
    if k > min_k:
        test = np.where(test >= len(DTindex), -1, test)
    return test, scores
