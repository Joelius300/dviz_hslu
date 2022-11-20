# DVIZ HSLU HS22 - Joel L.

## META - TO REMOVE

7200 - 9000 characters incl. spaces

### Questions

- how detailed should the data analysis/exploration part be?

## Motivation

In 2019, I got the opportunity to interface the heating unit in our house with a serial port
and it didn't take long for me to start a real-time dashboard around the data I managed to extract
to help me find my footing in the world of web development and build a full-stack application from A to Z.
The heating unit outputs a stream of CSV data containing the the current values of the sensors within.
At first I only used this data for the dashboard in real-time but soon I started storing it in 10 min intervals
and in lockdown 2020 I switched to archiving in 1 min intervals. \
This data source allowed me to build a tool for my family with which they can check the current temperatures
without having to go down to the actual furnance.
This is especially helpful because it's a wood furnance so you have to manually put in wood and
light it when you see the temperature is running low. \
I also plan to use this data to train a forecasting model in hopes of further optimizing timing
for firing up the furnance and the amount of wood we use.

However, this dashboard I built is from a time where I understood very little about the heating unit and therefore it's
just numbers on a screen without much thought behind them and also very boring from a visualization point of view. \
With this project I would like to change this and learn how to correctly identify needs and how to build an
intuitive and helpful visualization around the data I collected.

The different components for extracting the data, storing it, making it consumable (API) and displaying it (web UI / dashboard),
etc. are all [Open Source](https://github.com/Joelius300/HeatingDataMonitor#Journey).

## Data exploration

This dataset has had my interest for quite a while now and I have already done some data exploration
and data analysis outside of this module. The many hours I have invested into this already were mostly
for my personal interest and general analysis of the dataset so I was able to use it in multiple modules.
In the work summary, I have only written down hours for the data exploration and data analysis where
DVIZ was an intended primary beneficiary. For the analysis done specifically for other modules I have of
course still taken the insights into account if they were relevant but did not count the hours towards
this project.

### Meaning of variables

Many of the variable names the heating data provides aren't very descriptive. To determine the meanings of the columns,
I read through the manual and interpreted electrical schemata trying to match sensors connected to familiarly named signal lines. \
Unfortunately, I did not manage to understand all the variables.

This analysis was done to better understand the dataset and allow usage of it in DVIZ and also partially DBS.
A few of the hours for this are included in the blanket data analysis work entry.

Below are the determined meanings of the columns I believe might be important or interesting for the dashboard.

- received_time: Time my system received this state of the heating unit in UTC
- kessel: Temperature of the water inside the furnance in °C
- abgas: Temperature of exhaust gasses in °C
- co2_soll: Target value of CO2 percentage.
- co2_ist: Actual CO2 percentage. Can be transformed into residual oxygen percentage with formula: O2 = 20.942 - CO2 * 20.942 / 20.35 (note that 20.942=O2 max and 20.35 CO2 max for wood).
- puffer_oben: Temperature in °C of buffer at the highest point (usually highest temperature because the water is layered by temperature ascending). Used for determining the stored energy.
- puffer_unten: ditto but lowest point of the buffer (usally lowest temperature)
- betriebsphase_kessel: Phase of the furnance: 
  - 0=Off
  - 1=Heating up (Anheizen)
  - 2=Automatic (Automatik)
  - 4=Burn out (Ausbrennen)
  - 6=Regulate (Abregeln="slow down, its too hot")
  - 8=Heating up detected (Anheizen erkannt)
  - These are not used apparently: 3,5,7
  - "Lid open" (Tür geöffnet) exists according to the manual but the phase doesn't actually change when the lid is opened; can be fully replaced by DI_2
  - "Gluterhaltung" and "Übertemperatur" I don't know but they're probably not in the data either.
- aussen: Temperature of sensor outside the house in °C (important note: sensor must not be reachable by the sun)
- vorlauf_hk1_ist: Current temperature of water just leaving the furnance or buffer to go to heating circuit 1 (radiators)
- vorlauf_hk1_soll: ditto but target value instead of current value
- betriebsphase_hk1: Phase of heating circuit 1 (radiators) (needs more analysis)
- vorlauf_hk2_ist: See hk1 but for heating circuit 2 (underfloor heating)
- vorlauf_hk2_soll: ditto
- betriebsphase_hk2: ditto
- boiler_1: Temperature of water inside boiler in °C (top)
- di_2: True=Primary lid closed, False=Primary lid open (the primary lid is where the wood is put in)
- a_w_0: Motor of secondary air lid (True=lid open)
- a_w_1: Motor of primary air lid (True=lid open)
- a_phase_0: Smoke suction fan (True=on) (Saugzuggebläse)


## Target audience

The target audience is my family with my dad being the most important stakeholder as he manages the heating unit the most. \
To determine the needs of this user, I had a meeting with him and we discussed the current workflows and how decisions are made
with the tools he has available at the moment.

## Visualization breakdown

## Tools and libraries

which and why

## Sources
