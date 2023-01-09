from datetime import datetime, timedelta

import numpy as np
import streamlit as st

from data import earliest_time, get_period, projected_hit_times, BUFFER_AVG, BUFFER_MIN
from plots import create_temperature_line_chart, BUFFER_MAX, DRINKING_WATER, construct_action_phrase
from shared import Thresholds, PROJECT_TIMEZONE

# This project makes heavy use of constants to increase readability and decrease complexity at the cost
# of decreased code reusability (for other projects).
# Note, that this does not really make the application less customizable and
# the relevant values to change for a customized experience are even neatly arranged and easy to find and update.

PROJECT_TITLE = "Heating unit dashboard"

DEFAULT_DATE_OFFSET = timedelta(days=3)
DEFAULT_LOWER_THRESHOLD = 30
DEFAULT_UPPER_THRESHOLD = 40

# st.date_input always formats as %Y/%m/%d apparently so we cope: https://github.com/streamlit/streamlit/issues/5234
DATE_FORMAT = "%Y/%m/%d"

# plot dimensions in pixels for two column layout in wide mode.
# Designed for full-hd screens (1920x1080) as responsiveness was not a requirement and hard to get right with Plotly.
PLOT_HEIGHT = 400
PLOT_WIDTH = 800

DEFAULT_YLIM = [20, 90]  # °C - same system and environment, so the limits should be universal to have a reference

# to avoid an overwhelming number of inputs and configurations, this is fixed for the application. However, in the real
# world this might be a value that's interesting to configure depending on the volume of the buffer, the type of wood
# used, the output of the furnace, etc.
SUGGESTED_FIRE_UP_TIME_BEFORE_THRESHOLD_CROSS = timedelta(hours=1)

st.set_page_config(layout="wide")
st.title(PROJECT_TITLE)

now = datetime.now(PROJECT_TIMEZONE)
today = now.date()

# initialize session state (once per user session -> only one "now" for consecutive runs, reload to get real now again)
# Only necessary because Streamlit runs the script again DURING date range selection, no clue why you would do that..
if 'period_from' not in st.session_state:
    st.session_state.period_from = now - DEFAULT_DATE_OFFSET
    st.session_state.period_to = now

# get user inputs
period_col, from_time_col, to_time_col, lower_threshold_col, upper_threshold_col = st.columns([2, 1, 1, 1, 1])

with period_col:
    if st.session_state.period_to:
        date_period_value = (st.session_state.period_from, st.session_state.period_to)
    else:  # user is currently selecting a range but only has selected the start of it.
        date_period_value = st.session_state.date_period_widget  # no change, this is Streamlit's value of the widget

    date_period = st.date_input("Period date range",
                                date_period_value,
                                min_value=earliest_time(),
                                max_value=today,
                                key="date_period_widget")

date_from, date_to = date_period[0], None
if len(date_period) >= 2:
    # No idea why Streamlit runs again with an incomplete range selected, makes absolutely no sense to me.
    date_to = date_period[1]

with from_time_col:
    # key needed, otherwise it's derived from the dynamic label text.
    # also using session state instead of now directly otherwise input from user may be overridden next minute.
    # see https://github.com/streamlit/streamlit/issues/678
    time_from = st.time_input(f"Period start time (on {date_from:{DATE_FORMAT}})",
                              value=st.session_state.period_from.time(), key="time_from_widget")

with to_time_col:
    formatted_date = f"{date_to:{DATE_FORMAT}}" if date_to else "-"
    if st.session_state.period_to:
        time_to_value = st.session_state.period_to.time()
    else:  # user is still selecting range, no period_to available -> don't change, just use previous internal value
        time_to_value = st.session_state.time_to_widget

    # no way to constrain max time directly. Instead of showing an error, we'll just let it slide, we're forecasters :)
    time_to = st.time_input(f"Period end time (on {formatted_date})",
                            value=time_to_value, key="time_to_widget")

period_from = datetime.combine(date_from, time_from)
period_from = period_from.astimezone(PROJECT_TIMEZONE)

if date_to:
    period_to = datetime.combine(date_to, time_to)
    period_to = period_to.astimezone(PROJECT_TIMEZONE)
else:
    period_to = None

st.session_state.period_from = period_from
st.session_state.period_to = period_to

with lower_threshold_col:
    lower_threshold = st.number_input("Lower threshold (°C)", min_value=20, max_value=50, value=DEFAULT_LOWER_THRESHOLD)

with upper_threshold_col:
    upper_threshold = st.number_input("Upper threshold (°C)", min_value=20, max_value=50, value=DEFAULT_UPPER_THRESHOLD)

# only stop after all the inputs are shown
if not period_to:
    st.write("Please select a range.")
    st.stop()

if (period_to - period_from) < np.timedelta64(5, "m"):
    st.write("Please select a longer period.")
    st.stop()

if lower_threshold >= upper_threshold:
    # Unfortunately I didn't find a way to do "client-side" validation for this (so that you cannot even select wrongly)
    st.write("Lower threshold must be below upper threshold.")
    st.stop()

current, data, predicted = get_period(period_from, period_to)

thresholds = Thresholds(upper_threshold, lower_threshold)
hit_times = projected_hit_times(data, predicted, thresholds)

# recommendation phrase
# requires unsafe html flag; it's apparently not possible to customize the font size of text content otherwise.
st.markdown(construct_action_phrase(hit_times, period_to, thresholds, SUGGESTED_FIRE_UP_TIME_BEFORE_THRESHOLD_CROSS,
                                    font_size="1.2rem"), unsafe_allow_html=True)

# temperature charts
col_stored_energy, col_drinking_water = st.columns(2)

with col_stored_energy:
    st.subheader("Buffer")

    fig = create_temperature_line_chart(data, predicted, [(BUFFER_MAX, False), (BUFFER_AVG, True), (BUFFER_MIN, True)],
                                        DEFAULT_YLIM, thresholds, PLOT_HEIGHT, PLOT_WIDTH)
    st.plotly_chart(fig)

with col_drinking_water:
    st.subheader("Drinking water")

    fig = create_temperature_line_chart(data, predicted, DRINKING_WATER,
                                        DEFAULT_YLIM, thresholds, PLOT_HEIGHT, PLOT_WIDTH)
    st.plotly_chart(fig)
