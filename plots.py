from datetime import datetime, timedelta
from numbers import Number

import humanize
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objs import Figure
import pandas as pd

from data import BUFFER_MIN, BUFFER_AVG, TIME, DRINKING_WATER, BUFFER_MAX, PREDICTED_PERIOD
from shared import is_in_winter_mode, HitTimes

TIME_LABEL = "Time"
DRINKING_WATER_LABEL = "Drinking water"
BUFFER_MAX_LABEL = "Buffer max"
BUFFER_MIN_LABEL = "Buffer min"
BUFFER_AVG_LABEL = "Buffer avg"

FAN_DEGREE_PER_MINUTE = 1 / (4 * 60)  # 1 deg uncertainty per 4 hours
FAN_INCREASE_PER_MINUTE = np.arange(1, PREDICTED_PERIOD / np.timedelta64(1, 's') + 10) * FAN_DEGREE_PER_MINUTE
PREDICTION_RESAMPLE_INTERVAL_MIN = 10

DEFAULT_YLIM = [10, 90]

LABELS = {
    TIME: TIME_LABEL,
    DRINKING_WATER: DRINKING_WATER_LABEL,
    BUFFER_MAX: BUFFER_MAX_LABEL,
    BUFFER_MIN: BUFFER_MIN_LABEL,
    BUFFER_AVG: BUFFER_AVG_LABEL
}

DRINKING_WATER_COLOR = "aqua"
BUFFER_MAX_COLOR = "orange"
BUFFER_MIN_COLOR = "azure"
BUFFER_AVG_COLOR = "green"

COLORS = {
    DRINKING_WATER: DRINKING_WATER_COLOR,
    BUFFER_MAX: BUFFER_MAX_COLOR,
    BUFFER_MIN: BUFFER_MIN_COLOR,
    BUFFER_AVG: BUFFER_AVG_COLOR
}

SUGGESTED_FIRE_UP_TIME_BEFORE_THRESHOLD_CROSS = timedelta(hours=1)


def create_temperature_line_chart(data: pd.DataFrame, predicted: pd.DataFrame, column: str,
                                  lower_threshold: float | int, upper_threshold: float | int,
                                  express=False):
    all_data = pd.concat([data, predicted])
    if not express:
        fig = go.Figure([_get_line(all_data, column, COLORS[column])], layout_hovermode="x", layout_yaxis_range=DEFAULT_YLIM)
    else:
        fig = px.line(all_data, x=all_data.index, y=column, labels=LABELS)
        fig.update_traces(hovertemplate=None, name=LABELS[column])
        fig.update_layout(hovermode="x", yaxis=dict(range=DEFAULT_YLIM))

    _add_threshold_line(fig, lower_threshold)
    _add_threshold_line(fig, upper_threshold)
    fig.add_vline(data.index[-1] + np.timedelta64(30, 's'), line_dash="dot", line_color="rgba(40, 40, 180, 0.8)")
    _add_prediction_fan(fig, predicted, column)

    return fig


def _add_prediction_fan(fig: Figure, predicted: pd.DataFrame, column: str):
    # resample to decrease resolution
    values = predicted[column].resample(f'{PREDICTION_RESAMPLE_INTERVAL_MIN}min').median()

    fan_deltas = FAN_INCREASE_PER_MINUTE[:len(values)] * PREDICTION_RESAMPLE_INTERVAL_MIN
    bounds = pd.DataFrame({'upper': values + fan_deltas, 'lower': values - fan_deltas}, index=values.index)

    rows_in_one_hour = int(np.timedelta64(1, 'h') / np.timedelta64(PREDICTION_RESAMPLE_INTERVAL_MIN, 'm'))

    # take the max/min over 1 hour rolling
    bounds['upper'] = bounds['upper'].rolling(rows_in_one_hour).max()
    bounds['lower'] = bounds['lower'].rolling(rows_in_one_hour).min()

    # an alternate solution which was explored is resampling again but this often results in predicted points
    # outside the prediction bounds when plotted with linear lines. Therefore, a higher resolution is used but smoothed.
    # bounds = bounds.resample("1h").apply({'upper': lambda g: g.max(), 'lower': lambda g: g.min()})

    # take a moving average over 1 hour rolling to smooth it out
    bounds = bounds.rolling(rows_in_one_hour).mean()

    # ensure the bounds aren't outside the values
    bounds['upper'] = bounds['upper'].clip(lower=values)
    bounds['lower'] = bounds['lower'].clip(upper=values)

    # ensure the fan has a smooth start from the initial prediction position after all the aggregation & smoothing
    first_temp, first_index = predicted[column].iloc[0], predicted.index[0]
    bounds = pd.concat([pd.DataFrame({'upper': [first_temp], 'lower': [first_temp]}, index=[first_index]), bounds])

    upper_line = go.Scatter(
        name="Upper prediction",
        x=bounds.index,
        y=bounds.upper,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    )

    lower_line = go.Scatter(
        name="Lower prediction",
        x=bounds.index,
        y=bounds.lower,
        mode='lines',
        line=dict(width=0),
        fillcolor='rgba(69, 69, 69, 0.25)',
        fill='tonexty',
        showlegend=False,
        hoverinfo="skip"
    )

    fig.add_trace(upper_line)
    fig.add_trace(lower_line)


def _add_threshold_line(fig: Figure, threshold: float | int):
    fig.add_hline(threshold, line_dash="dash", line_color="dark gray")  # TODO constants


def _get_line(data: pd.DataFrame, column: str, color):
    # TODO Fix hoverlabel to be formatted like plotly express
    return go.Scatter(x=data.index,
                      y=data[column],
                      mode="lines",
                      line=go.scatter.Line(color=color),
                      name=LABELS[column],
                      showlegend=False)


def add_detailed_buffer_lines(fig: Figure, data: pd.DataFrame, predicted: pd.DataFrame):
    for col in [BUFFER_MIN, BUFFER_AVG]:
        fig.add_trace(_get_line(pd.concat([data, predicted]), col, COLORS[col]))
        _add_prediction_fan(fig, predicted, col)
        # TODO determine if adding prediction makes sense.. But just stopping looks very bad..


def create_temperature_gauge(current, earlier, column, lower_threshold, upper_threshold):
    fig = go.Figure(go.Indicator(
        domain={'x': [0, 1], 'y': [0, 1]},
        value=current[column],
        mode="gauge+number+delta",
        title={'text': LABELS[column]},
        delta={'reference': earlier[column]},
        gauge={'axis': {'range': [20, 60]},
               'steps': [
                   {'range': [0, lower_threshold], 'color': "red"},
                   {'range': [lower_threshold, upper_threshold], 'color': "orange"}],
               'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': current[column]}
               }))

    return fig


def construct_action_phrase(hit_times: HitTimes, current_time: datetime,
                            lower_threshold: Number, upper_threshold: Number):
    """
    Constructs a phrase (str) describing the recommended action with relative times and additional information.

    :param hit_times: The projected hit times (return value of projected_hit_times())
    :param current_time: The (simulated) current time -> end of selected period
    :param lower_threshold: The lower threshold to cross. Must be the same threshold used for calculating hit_times.
    :param upper_threshold: The upper threshold to cross. Must be the same threshold used for calculating hit_times.
    :return: A human-readable phrase in the form of a string.
    """
    relevant_column = BUFFER_MAX if is_in_winter_mode(current_time) else DRINKING_WATER
    relevant_label = LABELS[relevant_column]
    relevant_hit_times = hit_times[relevant_column]

    def fmt_delta(time: datetime):  # format delta from current time (simulated current time = end of selected period)
        return humanize.naturaltime(time, when=current_time)

    def fmt_cross_phrase(threshold_label: str, threshold: Number, hit: datetime):
        verb = "fell" if hit < current_time else "will fall"
        hit_delta = fmt_delta(hit)
        return f"{relevant_label} {verb} below the {threshold_label} threshold ({threshold} °C) {hit_delta}."

    action_phrase = "No immediate action necessary."

    [high_hit, low_hit] = relevant_hit_times
    if low_hit:
        fire_up_time = low_hit - SUGGESTED_FIRE_UP_TIME_BEFORE_THRESHOLD_CROSS
        fire_up_delta = fmt_delta(fire_up_time) if fire_up_time > current_time else "as soon as possible"

        action_phrase = f"You should fire up **{fire_up_delta}**."
        cross_phrase = fmt_cross_phrase("lower", lower_threshold, low_hit)
    elif high_hit:
        cross_phrase = fmt_cross_phrase("upper", upper_threshold, high_hit)
    else:
        return action_phrase

    return f"{action_phrase} {cross_phrase}"
