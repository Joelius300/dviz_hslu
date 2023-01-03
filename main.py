from datetime import datetime, timedelta, time

import numpy as np
import pandas as pd
import pytz
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from plots import create_temperature_line_chart, create_temperature_gauge, TIME, BUFFER_MAX, DRINKING_WATER, LABELS

CSV_PATH = "data/heating-data_cleaned.csv"
SUMMER_PREDICTION_CSV_PATH = "data/summer_prediction.csv"
WINTER_PREDICTION_CSV_PATH = "data/winter_prediction.csv"
TIME_OFFSET = np.timedelta64(1, "Y")
tz = pytz.timezone("Europe/Zurich")

DEFAULT_DATE_OFFSET = timedelta(days=2)
DEFAULT_LOWER_THRESHOLD = 30
DEFAULT_UPPER_THRESHOLD = 40

PREDICTED_PERIOD = np.timedelta64(1, "D")

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
def load_predictions():
    def load_prediction(path):
        pred = pd.read_csv(path)
        pred.index = pd.to_datetime(pred.pop(TIME), utc=True)
        pred.index = pred.index.tz_convert(tz)
        return pred

    summer = load_prediction(SUMMER_PREDICTION_CSV_PATH)
    winter = load_prediction(WINTER_PREDICTION_CSV_PATH)

    return summer, winter


@st.cache
def earliest_time():
    return load_data().index.min()


def get_period(period_from, period_to):
    period_from, period_to = pd.to_datetime(period_from), pd.to_datetime(period_to)

    data = load_data()[period_from:period_to]
    current = data.iloc[-1]
    predicted = load_data()[period_to:period_to + PREDICTED_PERIOD]

    during_heating_up = predicted.query("heating_up")
    # if the prediction contains a heating process, we want to replace that part of it with a pre-defined prediction.
    # these pre-defined predictions are snippets of real data, namely in the places that go to the lowest temperature
    # naturally in the dataset. This means every other progression ends descending (= starts heating up again)
    # before the templates so the templates can be added onto the end without fear of not finding a continuation point.
    predicted_columns = [BUFFER_MAX, DRINKING_WATER]
    if not during_heating_up.empty:
        summer_pred, winter_pred = load_predictions()
        # select correct prediction template; in summer it's much longer and less steep than in winter
        prediction_template = winter_pred if period_to.month < 5 or period_to.month >= 10 else summer_pred
        heating_up_row = during_heating_up.reset_index().iloc[0]
        first_time_heating_up = heating_up_row[TIME]
        # determine best matching point in the prediction template using the sum of squared errors
        SSE = (prediction_template[predicted_columns] - heating_up_row[predicted_columns]).pow(2).sum(axis=1)
        best_matching_point_in_template = SSE.idxmin()

        prediction_end_time = best_matching_point_in_template + PREDICTED_PERIOD
        prediction_template = prediction_template[best_matching_point_in_template:prediction_end_time]
        # move predicted times to the cut off point
        prediction_template.index = prediction_template.index - (prediction_template.index[0] - first_time_heating_up)
        # cut off from the point of first heating up and add prediction template from best matching time until the end
        predicted = pd.concat([predicted[:first_time_heating_up].iloc[:-1], prediction_template])

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

current, data, predicted = get_period(period_from, period_to)

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
