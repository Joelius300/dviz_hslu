from datetime import datetime, timedelta
from numbers import Number
from typing import List, Tuple, Literal

import humanize
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.graph_objs import Figure

from data import BUFFER_MIN, BUFFER_AVG, DRINKING_WATER, BUFFER_MAX, PREDICTED_PERIOD
from shared import is_in_winter_mode, HitTimes, Thresholds, rgba, rgb

DRINKING_WATER_LABEL = "Drinking water"
BUFFER_MAX_LABEL = "Buffer maximum"
BUFFER_MIN_LABEL = "Buffer minimum"
BUFFER_AVG_LABEL = "Buffer average"

DRINKING_WATER_COLOR = (0, 0, 139)  # "darkblue"
BUFFER_MAX_COLOR = (255, 165, 0)  # "orange"
BUFFER_MIN_COLOR = (30, 144, 255)  # "dodgerblue"
BUFFER_AVG_COLOR = (230, 160, 288)  # some pink - previously (50, 205, 50)  # "limegreen"

THRESHOLD_LINE_COLOR = "dark gray"
THRESHOLD_LINE_DASH = "dot"
THRESHOLD_LINE_OPACITY = .8

PREDICTION_SHADOW_COLOR = (227, 227, 232)  # secondary background (chart background) = (240, 242, 246) - (13, 15, 14)
PREDICTION_SHADOW_OPACITY = 1

FAN_OPACITY = .25

# contender for parameter but not necessary for this project
FAN_DEGREE_PER_MINUTE = 1 / (4 * 60)  # 1 deg uncertainty per 4 hours
FAN_INCREASE_PER_MINUTE = np.arange(1, PREDICTED_PERIOD / np.timedelta64(1, 's') + 10) * FAN_DEGREE_PER_MINUTE
FAN_RESAMPLE_INTERVAL_MIN = 10

LABELS = {
    DRINKING_WATER: DRINKING_WATER_LABEL,
    BUFFER_MAX: BUFFER_MAX_LABEL,
    BUFFER_MIN: BUFFER_MIN_LABEL,
    BUFFER_AVG: BUFFER_AVG_LABEL
}

COLORS = {
    DRINKING_WATER: DRINKING_WATER_COLOR,
    BUFFER_MAX: BUFFER_MAX_COLOR,
    BUFFER_MIN: BUFFER_MIN_COLOR,
    BUFFER_AVG: BUFFER_AVG_COLOR
}


def create_temperature_line_chart(data: pd.DataFrame, predicted: pd.DataFrame,
                                  columns: str | List[Tuple[str, bool]], ylim: List[int],
                                  thresholds: Thresholds,
                                  plot_height: int, plot_width: int) -> Figure:
    """
    Creates a Plotly chart displaying one or more temperature time-series. Data up to the present time is
    plotted with a slightly darker background. Predicted data is plotted with an additional fan to show increasing
    uncertainty over time. Additionally, temperature thresholds are plotted as horizontal lines.

    :param data: The data in the past (up to now) with a time-index and the columns specified in 'columns'.
    :param predicted: The predicted data following directly after 'data' also with a time-index and the same columns.
    :param columns: Either a single string to represent a single column, or a list of string-bool tuples each containing
           The name of a column and whether the line should be hidden initially.
    :param ylim: The inital y-limits to set. Must be a list with two items: [lower_limit, upper_limit]
    :param thresholds: The temperature thresholds to plot.
    :param plot_height: The height of the chart in pixels.
    :param plot_width: The width of the chart in pixels.
    :return: A Plotly Figure representing the created chart.
    """
    all_data = pd.concat([data, predicted])
    fig = go.Figure(layout=go.Layout(
        hovermode="x",
        yaxis=go.layout.YAxis(
            range=ylim,
            ticksuffix=" °C",
        ),
        margin=go.layout.Margin(
            t=40, b=0,  # just enough for the Plotly menu bar
            l=40, r=0,  # compensate for the removed axis title
        ),
        height=plot_height,
        width=plot_width,
        # group temperatures with their prediction fans in legend (wrong type annotation by Plotly)
        legend_traceorder="grouped",
    ))

    def add_temperature_line(col, hidden=False):
        fig.add_trace(_create_line_trace(all_data, col, rgb(*COLORS[col]), hidden=hidden))
        _add_prediction_fan(fig, predicted, col, hidden=hidden)

    if isinstance(columns, str):
        add_temperature_line(columns)
    else:  # must be list of tuples with column name and hidden flag
        for col, hidden in columns:
            add_temperature_line(col, hidden)

    _add_threshold_line(fig, thresholds.lower, "Lower")
    _add_threshold_line(fig, thresholds.upper, "Upper")
    _add_prediction_shadow(fig, data.index[0], predicted.index[0])

    return fig


def _add_prediction_fan(fig: Figure, predicted: pd.DataFrame, column: str, *, hidden=False):
    # resample to decrease resolution (drop na, the plot just connects all points so basically free LERP)
    values = predicted[column].resample(f'{FAN_RESAMPLE_INTERVAL_MIN}min').median().dropna()

    fan_deltas = FAN_INCREASE_PER_MINUTE[:len(values)] * FAN_RESAMPLE_INTERVAL_MIN
    bounds = pd.DataFrame({'upper': values + fan_deltas, 'lower': values - fan_deltas}, index=values.index)

    rows_in_one_hour = int(np.timedelta64(1, 'h') / np.timedelta64(FAN_RESAMPLE_INTERVAL_MIN, 'm'))

    # take the max/min over 1 hour rolling
    bounds['upper'] = bounds['upper'].rolling(rows_in_one_hour, min_periods=1).max()
    bounds['lower'] = bounds['lower'].rolling(rows_in_one_hour, min_periods=1).min()

    # an alternate solution which was explored is resampling again but this often results in predicted points
    # outside the prediction bounds when plotted with linear lines. Therefore, a higher resolution is used but smoothed.
    # bounds = bounds.resample("1h").apply({'upper': lambda g: g.max(), 'lower': lambda g: g.min()})

    # take a moving average over 1 hour rolling to smooth it out
    bounds = bounds.rolling(rows_in_one_hour, min_periods=2).mean()

    # ensure the bounds aren't outside the values
    bounds['upper'] = bounds['upper'].clip(lower=values)
    bounds['lower'] = bounds['lower'].clip(upper=values)

    # ensure the fan has a smooth start from the initial prediction position after all the aggregation & smoothing
    first_temp, first_index = predicted[column].iloc[0], predicted.index[0]
    bounds = pd.concat([pd.DataFrame({'upper': [first_temp], 'lower': [first_temp]}, index=[first_index]),
                        bounds[first_index + np.timedelta64(1, "s"):]])  # add a second to avoid collisions/duplicates

    shared_trace_props = dict(
        x=bounds.index,
        mode="lines",
        line_width=0,
        showlegend=False,
        hoverinfo="skip",
        legendgroup=LABELS[column]
    )

    if hidden:
        shared_trace_props["visible"] = "legendonly"

    fig.add_trace(go.Scatter(
        name="Upper prediction",
        y=bounds.upper,
        **shared_trace_props
    ))

    fig.add_trace(go.Scatter(
        name="Lower prediction",
        y=bounds.lower,
        fillcolor=rgba(*COLORS[column], a=FAN_OPACITY),
        fill='tonexty',
        **shared_trace_props
    ))


def _add_prediction_shadow(fig: Figure, start, end):
    fig.add_shape(go.layout.Shape(
        type="rect",
        xref="x",
        yref="paper",
        x0=start,
        y0=-0.001,
        x1=end,
        y1=1,
        fillcolor=rgb(*PREDICTION_SHADOW_COLOR),
        opacity=PREDICTION_SHADOW_OPACITY,
        layer="below",
        line_width=0,  # once again, Plotly not using the correct type annotations for kwargs
    ))


def _add_threshold_line(fig: Figure, threshold: float | int, threshold_name: Literal["Lower", "Upper"]):
    fig.add_hline(threshold,
                  line_dash=THRESHOLD_LINE_DASH,
                  line_color=THRESHOLD_LINE_COLOR,
                  opacity=THRESHOLD_LINE_OPACITY,
                  annotation_position="top right",
                  annotation=go.layout.Annotation(
                      text=f"{threshold_name} threshold",
                      hovertext=f"{threshold} °C",
                      # hacky way to force annotation outside the plot area onto the legend.
                      # values are designed only for 'Lower threshold' and 'Upper threshold', which
                      # conveniently have the same number of letters. Couldn't find a prettier way sadly.
                      xshift=90,
                      yshift=-10
                  ))


def _create_line_trace(data: pd.DataFrame, column: str, color, *, hidden=False):
    trace = go.Scatter(x=data.index,
                       y=data[column],
                       mode="lines",
                       line_color=color,
                       name=LABELS[column],
                       showlegend=True,
                       legendgroup=LABELS[column])

    if hidden:
        trace.visible = "legendonly"

    return trace


def construct_action_phrase(hit_times: HitTimes, current_time: datetime, thresholds: Thresholds,
                            suggested_fire_up_time_before_threshold_cross: timedelta, font_size="1rem") -> str:
    """
    Constructs a phrase (html str) describing the recommended action with relative times and additional information.
    It has to be HTML to incorporate the font-size; Unfortunately, there is no option in streamlit to set an arbitrary
    font-size for text written in markdown.

    :param hit_times: The projected hit times (return value of projected_hit_times())
    :param current_time: The (simulated) current time -> end of selected period
    :param thresholds: The thresholds to cross. Must be the same thresholds used for calculating hit_times.
    :param suggested_fire_up_time_before_threshold_cross: Time delta between suggested firing-up-time and threshold-cross-time.
    :param font_size: A valid CSS font-size the phrase should have. No validation, make sure it's right.
    :return: A safe HTML string which represents a human-readable phrase for when to fire up again.
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

    upper_hit, lower_hit = relevant_hit_times
    if lower_hit:
        fire_up_time = lower_hit - suggested_fire_up_time_before_threshold_cross
        fire_up_delta = fmt_delta(fire_up_time) if fire_up_time > current_time else "as soon as possible"

        action_phrase = f"You should fire up <strong>{fire_up_delta}</strong>."
        cross_phrase = fmt_cross_phrase("lower", thresholds.lower, lower_hit)
    elif upper_hit:
        cross_phrase = fmt_cross_phrase("upper", thresholds.upper, upper_hit)
    else:
        return action_phrase

    return f'<p style="font-size: {font_size}">{action_phrase} {cross_phrase}</p>'
