import sys
import os
import pandas as pd

relevant_columns = [
    "received_time",
    "boiler_1",
    "puffer_oben",
    "puffer_unten",
    # there are tons of other interesting data points but for the
    # use cases defined for this project, these are enough.
]

column_mapping = {
    "boiler_1": "drinking_water",
    "puffer_oben": "buffer_max",
    "puffer_unten": "buffer_min"
}


def load_data(path: str):
    df = pd.read_csv(path, usecols=relevant_columns)
    return df.rename(columns=column_mapping)


def write_data(df: pd.DataFrame, path: str):
    return df.to_csv(path, encoding='utf-8', index=False)


if __name__ == "__main__":
    path = sys.argv[1]
    df = load_data(path)
    name, ext = os.path.splitext(path)
    write_data(df, name + "_cleaned" + ext)
