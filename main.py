from datetime import datetime, timedelta, time

import streamlit as st

from data import earliest_time, get_period, projected_hit_times
from plots import create_temperature_line_chart, BUFFER_MAX, DRINKING_WATER, construct_action_phrase
from project_constants import PROJECT_TITLE, PROJECT_TIMEZONE

DEFAULT_DATE_OFFSET = timedelta(days=2)
DEFAULT_LOWER_THRESHOLD = 30
DEFAULT_UPPER_THRESHOLD = 40

st.set_page_config(layout="wide")

today = datetime.utcnow().date()

st.title(PROJECT_TITLE)

period_col, from_time_col, to_time_col, lower_threshold_col, upper_threshold_col = st.columns([2, 1, 1, 1, 1])

with period_col:
    date_period = st.date_input("Period",
                                (today - DEFAULT_DATE_OFFSET, today),
                                min_value=earliest_time(),
                                max_value=today)

with from_time_col:
    time_from = st.time_input("Time from", value=time(0, 0, 0))

with to_time_col:
    time_to = st.time_input("Time to", value=time(23, 59, 59))

date_from = date_period[0]
if len(date_period) < 2:
    date_to = date_from
else:
    date_to = date_period[1]

period_from = datetime.combine(date_from, time_from)
period_to = datetime.combine(date_to, time_to)
period_from = period_from.astimezone(PROJECT_TIMEZONE)
period_to = period_to.astimezone(PROJECT_TIMEZONE)

with lower_threshold_col:
    lower_threshold = st.number_input("Lower threshold", min_value=20, max_value=50, value=DEFAULT_LOWER_THRESHOLD)

with upper_threshold_col:
    upper_threshold = st.number_input("Upper threshold", min_value=20, max_value=50, value=DEFAULT_UPPER_THRESHOLD)
    # TODO Constrain upper threshold to be above lower threshold

current, data, predicted = get_period(period_from, period_to)

since_index = max(0, len(data) - 60 * 1)  # todo this 60 * 1 should be a variable somewhere. some gauge delta time.
# it also needs to be very obvious what that delta is in the visualization, either by text or/and indicator in the chart
earlier = data.iloc[since_index]

hit_times = projected_hit_times(data, predicted, lower_threshold, upper_threshold)
st.write(construct_action_phrase(hit_times, period_to, lower_threshold, upper_threshold))
st.write(hit_times)

col_stored_energy, col_drinking_water = st.columns(2)

with col_stored_energy:
    st.subheader("Stored energy")

    # fig = create_temperature_gauge(current, earlier, BUFFER_MAX, lower_threshold, upper_threshold)
    # st.plotly_chart(fig)

    fig = create_temperature_line_chart(data, predicted, BUFFER_MAX, lower_threshold, upper_threshold)
    st.plotly_chart(fig)

with col_drinking_water:
    st.subheader("Drinking water")

    # fig = create_temperature_gauge(current, earlier, DRINKING_WATER, lower_threshold, upper_threshold)
    # st.plotly_chart(fig)

    fig = create_temperature_line_chart(data, predicted, DRINKING_WATER, lower_threshold, upper_threshold)
    st.plotly_chart(fig)

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
