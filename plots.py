from datetime import datetime, timedelta
from numbers import Number

import humanize
import plotly.express as px
import plotly.graph_objects as go

from shared import is_in_winter_mode, HitTimes

TIME = "received_time"
DRINKING_WATER = "drinking_water"
BUFFER_MAX = "buffer_max"
BUFFER_MIN = "buffer_min"

TIME_LABEL = "Time"
DRINKING_WATER_LABEL = "Drinking water"
BUFFER_MAX_LABEL = "Buffer max"
BUFFER_MIN_LABEL = "Buffer min"

LABELS = {
    TIME: TIME_LABEL,
    DRINKING_WATER: DRINKING_WATER_LABEL,
    BUFFER_MAX: BUFFER_MAX_LABEL,
    BUFFER_MIN: BUFFER_MIN_LABEL
}

DRINKING_WATER_COLOR = "aqua"
BUFFER_MAX_COLOR = "orange"
BUFFER_MIN_COLOR = "azure"

COLORS = {
    DRINKING_WATER: DRINKING_WATER_COLOR,
    BUFFER_MAX: BUFFER_MAX_COLOR,
    BUFFER_MIN: BUFFER_MIN_COLOR
}

SUGGESTED_FIRE_UP_TIME_BEFORE_THRESHOLD_CROSS = timedelta(hours=1)


def create_temperature_line_chart(data, predicted, column, lower_threshold, upper_threshold):
    fig = px.line(data, x=data.index, y=column, labels=LABELS)

    fig['data'][0]['line']['color'] = COLORS[column]
    fig.add_hline(lower_threshold, line_dash="dash", line_color="dark gray")
    fig.add_hline(upper_threshold, line_dash="dash", line_color="dark gray")
    fig.add_trace(
        go.Scatter(x=predicted.index,
                   y=predicted[column],
                   mode="lines",
                   line=go.scatter.Line(color="red"),  # TODO different color OR the fanning
                   showlegend=False))

    return fig


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
        fire_up_delta = fmt_delta(fire_up_time) if fire_up_time >= current_time else "as soon as possible"

        action_phrase = f"You should fire up **{fire_up_delta}**."
        cross_phrase = fmt_cross_phrase("lower", lower_threshold, low_hit)
    elif high_hit:
        cross_phrase = fmt_cross_phrase("upper", upper_threshold, high_hit)
    else:
        return action_phrase

    return f"{action_phrase} {cross_phrase}"
