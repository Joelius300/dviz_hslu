import plotly.express as px
import plotly.graph_objects as go

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


def create_temperature_line_chart(data, column, lower_threshold, upper_threshold):
    fig = px.line(data, x=data.index, y=column, labels=LABELS)

    fig['data'][0]['line']['color'] = COLORS[column]
    fig.add_hline(lower_threshold, line_dash="dash", line_color="dark gray")
    fig.add_hline(upper_threshold, line_dash="dash", line_color="dark gray")

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
