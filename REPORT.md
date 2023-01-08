# DVIZ HSLU HS22 - Joel L

## META - TO REMOVE

7200 - 9000 characters incl. spaces

PUT SOMEWHERE

```
# TODO maybe move plot dimensions and ylim into main and make them parameters for the appropriate functions
# the dimensions of the plot are some of the strongest contenders for parameters instead of constants.
# But because I employed constants so widely otherwise, which increased readability and decreased complexity at the cost
# of decreased code reusability (for other projects), I stayed consistent and used constants for plot dimensions too.
# Note: the application does not really get less customizable and the relevant values to change for a customized
# experience are even neatly arranged and easy to find and update.
```

Wäg colorblindness:

<https://www.color-blindness.com/coblis-color-blindness-simulator/>

viläch fingsch no besseri farbe süsch zmingst sägä dasmä dür klicke cha usprobiere und usefinge was was isch.
zum verwirrig z minimiere hiuft da o das d y-achse limits fix si das züg nid mega resized we d uswau vo lines verändert wird.

### Questions

- how detailed should the data analysis/exploration part be?
  only the most important parts!

## Motivation

In 2019, I got the opportunity to interface the heating unit in our house with a serial port,
and it didn't take long for me to start a real-time dashboard around the data I managed to extract
to help me find my footing in the world of web development and build a full-stack application from A to Z.
The heating unit outputs a stream of CSV data containing the current values of the sensors within.
At first, I only used this data for the dashboard in real-time, but soon I started storing it in 10 min intervals
and in lockdown 2020 I switched to archiving in 1 min intervals. \
This data source allowed me to build a tool for my family with which they can check the current temperatures
without having to go down to the actual furnace.
This is especially helpful because it's a wood furnace, so you have to manually put in wood and
light it when you see the temperature is running low. \
I also plan to use this data to train a forecasting model in hopes of further optimizing timing
for firing up the furnace and the amount of wood we use.

However, this dashboard I built is from a time when I understood very little about the heating unit, and therefore it's
just numbers on a screen without much thought behind them and also very boring from a visualization point of view. \
With this project I would like to change this, learn how to correctly identify needs and how to build an
intuitive and helpful visualization around the data I collected.

The different components for extracting the data, storing it, making it consumable (API) and displaying it (web UI / dashboard),
etc. are all [Open Source](https://github.com/Joelius300/HeatingDataMonitor).

## Target audience

The target audience is my family with my dad being the most important stakeholder as he manages the heating unit the most. \
To determine the needs of this user, I had a meeting with him, and we discussed the current workflows and how decisions are made
with the tools he has available at the moment.

### Persona

Some key information about my father as the target audience:

- Good understanding of the heating unit and the processes related to it
- Tech-savvier than many at their age but certainly needs good UX design to understand dashboard
- No visual impairments
- Decisions to make: When to fire up the furnace, when to get more wood (no data available)
- Current tools: Knowledge and experience, basic dashboard built by me

### Status quo

Before discussing the takeaways from the meeting, here is a brief explanation of the heating system in place.

Our house has both floor heating and radiators. Additionally, a storage water heater stores and maintains 600 liters of hot drinking water for all the water
outlets in the house. To provide heat to them, a log heating unit is in place which regularly has to be filled up with wood and lit on fire manually. As is custom,
the heat generated from burning the wood isn't (all) used to supply the heating circuits and storage water heater but is transferred into a buffer storage where
3000 liters of heating water are kept. The heat from this buffer is used to provide hot water to the consuming systems when the furnace isn't burning.

### Key takeaways

#### Existing process

My fathers current process to determine whether firing up is necessary using the existing dashboard is as follows:

Often times a gut feeling results in him checking the dashboard to see the current values. In winter, all the systems are active and the main source of heat
is the buffer. Since the top sensor shows the approximate maximum temperature, it is a hard limit for heating up other systems and used as the main reference
to determine if firing up is necessary. In summer however, the heating circuits are disabled, so only the drinking water is relevant and used as reference directly.
The thresholds he uses to determine the need for firing up are as follows: \
If the reference temperature (buffer max or drinking water) is above 40 °C, no action is necessary. \
If it is below 30 °C, it's certainly necessary to fire up, otherwise the house will cool quickly and no more warms showers are possible. \
If it is between, it depends on many more factors. Those factors include the number of people at home in the next days, whether a bath is desired,
the current and predicted weather, and more.

These thresholds alongside with a prediction can be used to recommend an optimal time to fire up the furnace. Still, a more detailed view of the data
should be available to assist manual decision-making with respect to the factors for which there is no data available.

#### Unknown temperature distribution in buffer

For heating up other systems, hot water is taken from the top of the buffer (flow), pushed through the heating circuits and returned into the bottom of the
buffer (return). When heating up the floor heating and the radiators, a lot of heat is lost, and the return is much colder than the flow leading to a low temperature
at the bottom of the buffer where the bottom sensor is. This can lead to negative spikes in buffer min before the water mixes and layers again.
On the other hand, when the water goes around the storage water heater to heat the water inside, it doesn't
lose nearly as much energy and the return is often warmer than the water previously at the bottom of the buffer. Respectively, this causes positive spikes in
buffer min that correlate with an increase in the drinking water temperature. \
Because of these processes happening at different intervals, it's very hard to determine if the majority of the water in the buffer is closer to the warmest,
or closer to the lowest temperature. When buffer max and buffer min are substantially different, especially when the upper threshold has already been crossed,
an inspection of the analog hardware sensors spread across the buffer is necessary to determine the best course of action.

On the dashboard there should be an option to show the buffer min for a rough estimation on the stored energy in the buffer. Due to the unknown distribution,
this is verbose and often optional information, which requires good knowledge of the system, and should be represented as such.

## Data exploration

This dataset has had my interest for quite a while now, and I have already done some data exploration
and data analysis outside this module. The many hours I have invested into this already were mostly
for my personal interest and general analysis of the dataset, so I was able to use it in multiple modules.
In the work summary, I have only written down hours for the data exploration and data analysis where
DVIZ was an intended primary beneficiary. For the analysis done specifically for other modules I have of
course still taken the insights into account if they were relevant but did not count the hours towards
this project.

### Key findings

#### Meaning of columns

Some columns required investigation to interpret correctly. One of which is the operation state of the furnace ("betriebsphase_kessel"), which uses an undocumented
discrete number encoding. In this project this column was used indirectly by reducing it to a boolean "heating_up" to rectify impossible predictions.

Here are the meanings of the used columns:

- received_time: Time my system received this state of the heating unit in UTC
- buffer_max: Temperature in °C of buffer at the highest point (usually highest temperature because the water is layered by temperature ascending). Used for determining the stored energy.
- buffer_min: Like buffer_max but lowest point of the buffer (usually lowest temperature)
- drinking_water: Temperature in °C of drinking water inside boiler at the highest point (highest temperature)
- heating_up: Whether the heating unit is in the process of heating up, initiated by hand

#### Heating progression to lowest point

In order to avoid showing impossible predictions, an analysis was done to determine a suiting past heating cycle that went as low as possible for the most relevant columns.
This heating progression (highest to lowest point) is then used to replace invalid parts of predicted progressions. Heating up in a prediction is invalid because it could
only happen if the user manually fired up and the user wants to see the progression if they don't fire up.

## Visualization breakdown

## Tools and libraries

which and why

## Sources
