from datetime import datetime, timedelta, time

import numpy as np
import pandas as pd
import pytz
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from plots import create_temperature_line_chart, create_temperature_gauge, TIME, BUFFER_MAX, DRINKING_WATER, LABELS

CSV_PATH = "data/heating-data_cleaned.csv"
TIME_OFFSET = np.timedelta64(1, "Y")
tz = pytz.timezone("Europe/Zurich")

DEFAULT_DATE_OFFSET = timedelta(days=2)
DEFAULT_LOWER_THRESHOLD = 30
DEFAULT_UPPER_THRESHOLD = 40

PREDICTED_PERIOD = timedelta(days=3)

st.set_page_config(layout="wide")


# entire dataset is cached and held in memory.
# if it was much bigger, periods with from/to could be cached instead.
@st.cache
def load_data():
    heating_data = pd.read_csv(CSV_PATH)
    timestamps = pd.to_datetime(heating_data.pop(TIME), utc=True)
    timestamps = timestamps + TIME_OFFSET  # shift everything 1 year into the future to have fake prediction values
    heating_data.index = timestamps
    heating_data.index = heating_data.index.tz_convert(tz)
    heating_data["heating_up_prev"] = heating_data["heating_up"].shift(1).fillna(False)
    return heating_data.sort_index()


@st.cache
def earliest_time():
    return load_data().index.min()


def get_period(period_from, period_to, iterations):
    data = load_data()[period_from:period_to]

    prediction_end_time = pd.to_datetime(period_to + PREDICTED_PERIOD)
    predicted = load_data()[period_to:prediction_end_time]
    after_to = load_data()[period_to:]

    current = data.iloc[-1]

    print(f"Predicted length: {len(predicted)}")
    for i in range(iterations):
        heating_up = predicted.query("heating_up")["heating_up"]
        if heating_up.empty:
            print("No more heating up in this period, stop")
            break

        first_time_heating_up = heating_up.index[0]
        last_not_heating_up = predicted.query(f'index < \'{first_time_heating_up}\'').iloc[-1]
        after_start_heating = after_to[first_time_heating_up:]
        times_it_changes = after_start_heating.query("not heating_up and heating_up_prev")

        if times_it_changes.empty:
            print(f"Heating state never changes during {after_start_heating.index[0]} to {after_start_heating.index[-1]}, stop")
            break

        done_heating_up_time = times_it_changes.index[0]

        after_done_heating = after_to[done_heating_up_time:]
        squared_difference = ((after_done_heating.query("not heating_up")[[BUFFER_MAX, DRINKING_WATER]] - last_not_heating_up[[BUFFER_MAX, DRINKING_WATER]])).pow(2).sum(axis=1)
        continuation_time = (squared_difference - after_done_heating["hours_to_next_heating"]).idxmin()
        delta_cut_out = continuation_time - first_time_heating_up
        matching_period = after_to[continuation_time:prediction_end_time+delta_cut_out]
        matching_period = matching_period.set_index(matching_period.index - delta_cut_out)

        print(f'Heating from {first_time_heating_up} to {done_heating_up_time}, cutting out {delta_cut_out} and replacing it with {continuation_time} (lowest SSE from BUF={last_not_heating_up[BUFFER_MAX]},DRI={last_not_heating_up[DRINKING_WATER]})')

        up_to_first_time_heating_up = predicted[:first_time_heating_up].iloc[:-1]
        predicted = pd.concat([up_to_first_time_heating_up, matching_period])

        # this kinda works now
        # however, it always takes the smallest difference, no matter how little that helps
        # you could add a guard that you only allow adding those where the time until the next
        # heating up is greater than 1 hour or so. But it would probably be better to just add something
        # to the SSE like 1/time_to_next_heating_up because more time = better but we take the min because
        # of the error. or just subtract in hours or so? This way those that give longer additions are favoured. Mabybe?
        # In the end, it's probably best to just store a fixed example progression, probably the one that goes to the
        # lowest temperature ever recorded in the dataset. Then you just find the best match in this progression
        # and take from there until the end. If it's not long enough, you repeat the lowest temperature until the end.

    return current, data, predicted


def projected_hit_times(to, lower_threshold, upper_threshold):
    predicted = load_data()[to:]
    buffer_below_upper = predicted.query(f'{BUFFER_MAX} < {upper_threshold}').index[0]
    buffer_below_lower = predicted.query(f'{BUFFER_MAX} < {lower_threshold}').index[0]
    drinking_water_below_upper = predicted.query(f'{DRINKING_WATER} < {upper_threshold}').index[0]
    drinking_water_below_lower = predicted.query(f'{DRINKING_WATER} < {lower_threshold}').index[0]

    return {
        BUFFER_MAX: [buffer_below_upper, buffer_below_lower],
        DRINKING_WATER: [drinking_water_below_upper, drinking_water_below_lower]
    }


today = datetime.utcnow().date()

st.title("Heating unit")

period_col, from_time_col, to_time_col, lower_threshold_col, upper_threshold_col = \
    st.columns([2, 1, 1, 1, 1])
# st.columns(5)

with period_col:
    date_period = st.date_input("Period",
                                (today - DEFAULT_DATE_OFFSET, today),
                                min_value=earliest_time(),
                                max_value=today)

with from_time_col:
    time_from = st.time_input(
        "Time from", value=time(hour=0, minute=0, second=0))

with to_time_col:
    time_to = st.time_input("Time to", value=time(
        hour=23, minute=59, second=59))

date_from = date_period[0]
if len(date_period) < 2:
    date_to = date_from
else:
    date_to = date_period[1]

period_from = datetime.combine(date_from, time_from)
period_to = datetime.combine(date_to, time_to)
period_from = period_from.astimezone(tz)
period_to = period_to.astimezone(tz)

with lower_threshold_col:
    lower_threshold = st.number_input(
        "Lower threshold", min_value=20, max_value=50, value=DEFAULT_LOWER_THRESHOLD)

with upper_threshold_col:
    upper_threshold = st.number_input(
        "Upper threshold", min_value=20, max_value=50, value=DEFAULT_UPPER_THRESHOLD)
    # TODO Constrain upper threshold to be above lower threshold

iterations = st.number_input("Iterations", min_value=0, max_value=1000, value=1)

current, data, predicted = get_period(period_from, period_to, iterations)

since_index = max(0, len(data) - 60 * 1)  # todo this 60 * 1 should be a variable somewhere. some gauge delta time.
# it also needs to be very obvious what that delta is in the visualization, either by text or/and indicator in the chart
earlier = data.iloc[since_index]

# st.write(projected_hit_times(period_to, lower_threshold, upper_threshold))

col_stored_energy, col_drinking_water = st.columns(2)

with col_stored_energy:
    st.subheader("Stored energy")

    # fig = create_temperature_gauge(current, earlier, BUFFER_MAX, lower_threshold, upper_threshold)
    # st.plotly_chart(fig)

    fig = create_temperature_line_chart(data, BUFFER_MAX, lower_threshold, upper_threshold)
    fig.add_trace(
        go.Scatter(x=predicted.index, y=predicted[BUFFER_MAX], mode="lines", line=go.scatter.Line(color="red"),
                   showlegend=False))
    st.plotly_chart(fig)

with col_drinking_water:
    st.subheader("Drinking water")

    # fig = create_temperature_gauge(current, earlier, DRINKING_WATER, lower_threshold, upper_threshold)
    # st.plotly_chart(fig)

    fig = create_temperature_line_chart(data, DRINKING_WATER, lower_threshold, upper_threshold)
    fig.add_trace(
        go.Scatter(x=predicted.index, y=predicted[DRINKING_WATER], mode="lines", line=go.scatter.Line(color="red"),
                   showlegend=False))
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
# Maybe read is too harsh but i think it would work if you explain why red is "emergency-like"
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
