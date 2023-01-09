from datetime import datetime, timedelta, time

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

# date_input always formats as %Y/%m%d apparently so we cope: https://github.com/streamlit/streamlit/issues/5234
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

now = datetime.now(PROJECT_TIMEZONE)
today = now.date()

# initialize session state (once per user session -> only one "now" for consecutive runs, reload to get real now again)
if 'period_from' not in st.session_state:
    st.session_state.period_from = now - DEFAULT_DATE_OFFSET
    st.session_state.period_to = now

st.title(PROJECT_TITLE)

period_col, from_time_col, to_time_col, lower_threshold_col, upper_threshold_col = st.columns([2, 1, 1, 1, 1])

with period_col:
    date_period = st.date_input("Period date range",
                                (st.session_state.period_from.date(), st.session_state.period_to.date()),
                                min_value=earliest_time(),
                                max_value=today,
                                key="date_period_widget")

date_from = date_period[0]
if len(date_period) < 2:
    # this treats clicking just one day and then deselecting the same as double-clicking that day. Alternatively,
    # execution could be halted with an error here. No idea why streamlit runs again with an incomplete range selected.
    date_to = date_from
else:
    date_to = date_period[1]

with from_time_col:
    # key needed, otherwise it's derived from the dynamic label text.
    # also using session state instead of now directly otherwise input from user may be overridden next minute.
    # see https://github.com/streamlit/streamlit/issues/678
    time_from = st.time_input(f"Period start time (on {date_from:{DATE_FORMAT}})",
                              value=st.session_state.period_from.time(), key="time_from_widget")

with to_time_col:
    # no way to constrain max time directly. Instead of showing an error, we'll just let it slide, we're forecasters :)
    time_to = st.time_input(f"Period end time (on {date_to:{DATE_FORMAT}})",
                            value=st.session_state.period_to.time(), key="time_to_widget")


period_from = datetime.combine(date_from, time_from)
period_to = datetime.combine(date_to, time_to)
period_from = period_from.astimezone(PROJECT_TIMEZONE)
period_to = period_to.astimezone(PROJECT_TIMEZONE)

st.session_state.period_from = period_from
st.session_state.period_to = period_to

with lower_threshold_col:
    lower_threshold = st.number_input("Lower threshold", min_value=20, max_value=50, value=DEFAULT_LOWER_THRESHOLD)

with upper_threshold_col:
    upper_threshold = st.number_input("Upper threshold", min_value=20, max_value=50, value=DEFAULT_UPPER_THRESHOLD)

if (period_to - period_from) < np.timedelta64(5, "m"):
    st.write("Please select a longer period.")
    st.stop()

if lower_threshold >= upper_threshold:
    # Unfortunately I didn't find a way to do "client-side" validation for this (so that you cannot even select wrongly)
    st.write("Lower threshold must be below upper threshold.")
    st.stop()

thresholds = Thresholds(upper_threshold, lower_threshold)

current, data, predicted = get_period(period_from, period_to)

since_index = max(0, len(data) - 60 * 1)  # todo this 60 * 1 should be a variable somewhere. some gauge delta time.
# it also needs to be very obvious what that delta is in the visualization, either by text or/and indicator in the chart
earlier = data.iloc[since_index]

hit_times = projected_hit_times(data, predicted, thresholds)
st.write(construct_action_phrase(hit_times, period_to, thresholds, SUGGESTED_FIRE_UP_TIME_BEFORE_THRESHOLD_CROSS))

col_stored_energy, col_drinking_water = st.columns(2)

with col_stored_energy:
    st.subheader("Buffer")

    # fig = create_temperature_gauge(current, earlier, BUFFER_MAX, lower_threshold, upper_threshold)
    # st.plotly_chart(fig)

    fig = create_temperature_line_chart(data, predicted, [(BUFFER_MAX, False), (BUFFER_AVG, True), (BUFFER_MIN, True)],
                                        DEFAULT_YLIM, thresholds, PLOT_HEIGHT, PLOT_WIDTH)
    st.plotly_chart(fig)
    st.write(fig.to_dict())

with col_drinking_water:
    st.subheader("Drinking water")

    # fig = create_temperature_gauge(current, earlier, DRINKING_WATER, lower_threshold, upper_threshold)
    # st.plotly_chart(fig)

    fig = create_temperature_line_chart(data, predicted, DRINKING_WATER,
                                        DEFAULT_YLIM, thresholds, PLOT_HEIGHT, PLOT_WIDTH)
    st.plotly_chart(fig)
    st.write(fig.to_dict())

# TODO
# Line chart with average stored energy ((puffer oben + puffer unten) / 2) fan'd out to 50% on each site.
# Line color green or yellow (just try). fan color just a lighter, more translucent color.
# By default hidden but optionally displayed: The actual puffer oben and puffer unten values with red (or orange) and blue lines.
# Legend maybe above?
# Additionally, display a lower and upper threshold with a dashed or dotted line (in black?) but make sure it's not the same
# as the cursor indicator line.
# If you have enough time add a water buffer tank to the right of it with red at the top phasing out downwards
# and blue at the bottom phasing out upwards with either the respective low/high values or the average value in the center.
# The whole thing should be zoomable and panable
# Data is selected with a time selector
# Last week or 5 days by default
# Then another chart with the same lower and upper threshold and the same time selection, which just shows a line for the
# boiler temp. These thresholds should be configurable just like the time selection.

# Notes:
# - In summer the boiler is important, in winter the buffer
# - The dashboard is meant for current data and supposed to assist in the analytical task of determining the next best
#   point in time for firing up the furnace. Old data may be interesting to look at but not the main purpose of it.
# - the drinking water temperature doesn't make sense, it of course can never be heated above the maximum stored energy
#   (it can stay there longer than the buffer sure but it can't rise above the buffer max!)

# Feedback:
# - Danger zone -> alert (just mention that, in the end this is a dashboard, not an app)
# - Very clear indication to get an instruction without having to analyze the chart -> light signal (and maybe a time estimate)
# - Shift data maybe by 1 year back so you have access to "future" values
# - Compare summer and winter and try to analyze whether or not the the average is even meaningful (in winter)
# - Maybe show the real data by default and have a simplified checkbox instead of a detailed to show the average
#   -> she's concerned that the average of the two points are misleading or not helpful when the real
#      distribution is unknown
# - Maybe figure out which is more important for the decision, buffer max, buffer min or average.
#   -> Dad says the max is (much) more important currently but the average might give interesting insight

# Feedback 2:
# Bar (gauge) chart 20-60 make sense? otherwise 0-100 maybe?
# In the gauge maybe avoid the bar but use a symbol (point) instead, because the position is important, not the length
# -> Only have the bar if it's length encodes something meaningful or not
# Maybe red is too harsh but i think it would work if you explain why red is "emergency-like"
# Split functions out into it's own module with the main.py only being for the dashboard/layouting/etc.
# have plotly emit some events (custom streamlit plotly component) for the shared zoom
# VISUALIZATION IS THE PART THAT MATTERS! not really ux or things like that, the viz has to make sense. focus on that!
# -> this also means that shared zoom, localization, etc. is all lowest priority!
# -> this extends to the constraint that the upper threshold is above the lower one

# Questions I didnt ask:
# - Visual buffer drawn next to it (probably not helpful or impressive, think we can ignore that)
# - Conversion into kwh or smth like that but what out she's a physicist so it would have to be right and that's hard

# Feedback vo dä studis
# weniger kontrastende Farben also blau isch hert trash
