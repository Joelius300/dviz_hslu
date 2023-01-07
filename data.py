from datetime import datetime
from typing import Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st

from project_constants import PROJECT_TIMEZONE
from shared import is_in_winter_mode, HitTimes, Thresholds, ThresholdCrossings

CSV_PATH = "data/heating-data_cleaned.csv"
SUMMER_PREDICTION_CSV_PATH = "data/summer_prediction.csv"
WINTER_PREDICTION_CSV_PATH = "data/winter_prediction.csv"

TIME = "received_time"
DRINKING_WATER = "drinking_water"
BUFFER_MAX = "buffer_max"
BUFFER_MIN = "buffer_min"
BUFFER_AVG = "buffer_avg"
# TODO constant for heating_up and heating_up_prev

TIME_OFFSET = np.timedelta64(1, "Y")

PREDICTED_PERIOD = np.timedelta64(3, "D")
PREDICTED_COLUMNS = [BUFFER_MAX, DRINKING_WATER]
HIT_POINT_DETECTION_PAST_OFFSET = np.timedelta64(-1, "D")


# entire dataset is cached and held in memory.
# if it was much bigger, periods with from/to could be cached instead.
@st.cache
def load_data():
    """
    Loads and prepares the dataset. Times are shifted by 1 year to get data from early 2021 to late 2023
    which allows for fake-predictions using real data and still allows exploration in the past.
    """
    heating_data = pd.read_csv(CSV_PATH)
    timestamps = pd.to_datetime(heating_data.pop(TIME), utc=True)
    timestamps = timestamps + TIME_OFFSET  # shift everything 1 year into the future to have fake prediction values
    heating_data.index = timestamps
    heating_data.index = heating_data.index.tz_convert(PROJECT_TIMEZONE)
    heating_data["heating_up_prev"] = heating_data["heating_up"].shift(1).fillna(False)
    heating_data[BUFFER_AVG] = (heating_data[BUFFER_MAX] + heating_data[BUFFER_MIN]) / 2
    return heating_data.sort_index()


@st.cache
def load_prediction_templates():
    """Loads the prediction templates for summer and winter (returned in a 2-tuple in that order)."""

    def load_prediction(path) -> pd.DataFrame:
        # TODO extract redundancies with load_data()
        pred = pd.read_csv(path)
        pred.index = pd.to_datetime(pred.pop(TIME), utc=True)
        pred.index = pred.index.tz_convert(PROJECT_TIMEZONE)
        pred[BUFFER_AVG] = (pred[BUFFER_MAX] + pred[BUFFER_MIN]) / 2
        return pred

    summer = load_prediction(SUMMER_PREDICTION_CSV_PATH)
    winter = load_prediction(WINTER_PREDICTION_CSV_PATH)

    return summer, winter


@st.cache
def earliest_time() -> datetime:
    """Returns the earliest recorded time in the dataset."""
    return load_data().index.min()


def get_period(period_from: datetime, period_to: datetime) -> Tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """
    Fetches data in a certain period of time including a forecast prediction right after the end of the period.

    :param period_from: Timestamp for the start of the period.
    :param period_to: Timestamp for the end of the period.
    :return: A 3-tuple with the current value (at period end), the past data (during period) and predicted data
             (after period).
    """
    period_from, period_to = pd.to_datetime(period_from), pd.to_datetime(period_to)

    data = load_data()[period_from:period_to]
    current = data.iloc[-1]
    predicted = load_data()[period_to:period_to + PREDICTED_PERIOD]

    during_heating_up = predicted.query("heating_up")
    # if the prediction contains a heating process, we want to replace that part of it with a pre-defined prediction.
    # these pre-defined predictions are snippets of real data, namely in the places that go to the lowest temperature
    # naturally in the dataset. This means every other progression ends descending (= starts heating up again) before
    # the templates so the templates can be added onto the end with less fear of not finding a continuation point.
    if not during_heating_up.empty:
        summer_pred, winter_pred = load_prediction_templates()
        # select correct prediction template; in summer it's much longer and less steep than in winter
        prediction_template = winter_pred if is_in_winter_mode(period_to) else summer_pred
        heating_up_row = during_heating_up.reset_index().iloc[0]
        first_time_heating_up: datetime = heating_up_row[TIME]
        # determine best matching point (time) in the prediction template using the sum of squared errors
        sse = (prediction_template[PREDICTED_COLUMNS] - heating_up_row[PREDICTED_COLUMNS]).pow(2).sum(axis=1)
        best_match_in_template: datetime = sse.idxmin()

        # template end time: from the best matching point, take data to complete the PREDICTED_PERIOD together with
        # the real data (before heating up)
        template_prediction_end_time = best_match_in_template + PREDICTED_PERIOD - (first_time_heating_up - period_to)
        prediction_template = prediction_template[best_match_in_template:template_prediction_end_time]
        # move predicted times to the cut off point
        prediction_template.index = prediction_template.index - (prediction_template.index[0] - first_time_heating_up)
        # cut off from the point of first heating up and add prediction template from best matching time until the end
        predicted = pd.concat([predicted[:first_time_heating_up], prediction_template])

    return current, data, predicted


def projected_hit_times(data: pd.DataFrame, predicted: pd.DataFrame, thresholds: Thresholds):
    """
    Returns the projected (or past) times when values first passed the thresholds.

    :param data: The past data in the period just before the predicted data.
    :param predicted: The predicted data in the period just after the past data.
    :param thresholds: The lower and upper thresholds to cross.
    :return: A dictionary with one entry per PREDICTED_COLUMNS. Each entry contains the first time the upper and
             lower thresholds are crossed respectively. If it didn't cross the threshold in the predicted data,
             or in HIT_POINT_DETECTION_PAST_OFFSET of the past data, then the timestamp is NULL instead.
    """

    def projected_hit_times_core(period: pd.DataFrame):
        hit_times: HitTimes = {}
        for col in PREDICTED_COLUMNS:
            first_below_upper = period.query(f'{col} < {thresholds.upper}').first_valid_index()
            first_below_lower = period.query(f'{col} < {thresholds.lower}').first_valid_index()
            hit_times[col] = ThresholdCrossings(first_below_upper, first_below_lower)

        return hit_times

    hit_times = projected_hit_times_core(predicted)

    # if the projected hit point is the first possible point, chances are the hit point was actually in the past.
    # so query that and adjust accordingly if necessary.
    first_predicted_time: datetime = predicted.index[0]
    # query only for upper here because upper must be crossed before lower
    first_hitters = [col for col, hits in hit_times.items() if hits.upper == first_predicted_time]
    if first_hitters:
        past_data = data[first_predicted_time + HIT_POINT_DETECTION_PAST_OFFSET:]
        past_hit_times = projected_hit_times_core(past_data)
        for col in first_hitters:
            # use the past one instead for the first hitters, if there are any
            upper, lower = hit_times[col]
            past_upper, past_lower = past_hit_times[col]
            upper = past_upper if past_upper else upper
            lower = past_lower if past_lower else lower
            hit_times[col] = ThresholdCrossings(upper, lower)

    return hit_times
