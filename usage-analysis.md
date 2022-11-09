# Heating data analysis tool - usage analysis

Date: 05.11.22
Participants: me, my dad

## Varia

- In Summer only the boiler is of interest because the two HKs are disabled (and the boiler doesn't fully drain the buffers so even though the buffers still show as warm, a heating cycle is necessary)
- In Winter (mostly) the buffers are of interest because the two HKs are also constantly draining them and they can drain them fully
- Non-linear nature of energy stored and current temperature of boiler and puffers because there's a mixer (and ventil ?) that ensures only a certain max temperature goes into the HKs and the drinking water lines. For the boiler cold drinking water is mixed in and for the HKs the rücklauf is mixed in. That means when the buffers are 80° and 10 liters of water are put into the HK1, they don't loose 10 liters of 80° but much less since it's mixed with colder water. Therefore the buffers and boiler lose energy much quicker once they go below the max temperature thresholds.
- Rücklauf = coming back from the HK's / boiler, Vorlauf = going in the HK's / boiler
- In summer the buffers are often close to equal meaning the whole 3k liters are about the same temperature because it's a slow drain (only from the boiler; and the boiler also has a much warmer Rücklauf then the HK's)
- In winter (because you fire up much more often) there a much bigger potential difference between the coldest part of the buffers and the warmest part but since the data only shows those two and not any of the 4 sensors between, you don't know what the ratio is. In witer it's possible that 3/4 are 20° and the top quarter is 70° but it could just as well be the other way around and the data would show the same thing. This is a case where a physical check is necessary.
- The kind of wood has a large influence on the amount of energy it yields, almost impossible to account for.
- Small box with which the temperature of the individual hks (not hk1,2 but per room etc.) can be adjusted. This is interfacing with the valves in the cellar but these are not connected to the furnance and cannot be interfaced with the data etc. They can only deliver as much energy as the furnance provides.

## Questions

- by whom will the tool be used and for what (YOU ARE NOT THE USER)
  - who do they report to: yourself

## Ideas

- the hard-caps 30° and 40° for boiler in summer and puffer oben in winter could be done with red / green and between is orange (watch out for accessibility issues). Maybe something with gauge.
- correlation between aussen temp and time between firing up so x-axis would be the average of the aussen temp during the heating time and y-axis length of the heating time (between firing up).
- area under kessel from the initial startup (door open) until betriebsphase=aus and kessel < 30° would give a measure of generated energy. Another measure of generated energy is in the buffers. For now it may be easier to ignore boiler as it's much less predictable.
  Compare this kessel energy to the duration it lasted (to be defined more precisely) with a dependency on the aussen temp.
- "Energy chart" which is just the average of puffer oben and puffer unten. Not perfect because we don't know the ratio (it's not linear, see above) but probably one of the best metrics we have.
- Maybe this all could come together in a dashboard where one chart shows kessel, aussen and the average of the buffers (this value would be filled and puffer oben and unten would also be there as dashed lines), a control allows jumping to the next and previous heating cycle (from firing up to next firing up), another allows timespan selection for more fine-grained control and somehow a metric and or chart needs to display the relation of the area of the stored energy in the buffers (area under the average line, unit would be °C hours), the generated energy (area und the kessel line from firing up to the point where the betriebsphase becomes Aus) and the aussen temp. Make it zoomable and potentially even panable.
- Running a WMA over the data would probably make sense for the visualization to minimize jitter.

### what processes are they following

#### Is it time to fire up the furnance

- usually it's a feeling like the warm water isn't warm or the floor is cold etc which prompt check to current values
- the values to check are Boiler (in summer) and Puffer Oben and Puffer Unten (in winter)
- to decide when to fire up
  - it's mostly experience
  - under 30° is a must, over 40° usually doesn't require action and 30-40° needs a bit of thinking/analysis (is it below a certain threshold e.g. 40° -> you know it's going to cool down fast so action is more urgent)
  - what's planned for the next few hours and days, e.g. are you away for a few days but need to keep the house warm for others or is it morning and you know you'll need quite a bit of energy until the evening or is it already evening and you know it's going to be enough throughout the night and can fire up tomorrow morning. Are there plans to take a bath? How many people are (going to be) in the house? stuff like this

#### Checking the temperature outside

- looking at the aussen values

  - what decision do they need to make
    - to fire up or not
    - to get more wood (how much wood is left)
    - who does it (do you have time)
  - what are the current criteria for making that decision -> see above
  - "how are you working right now?" -> see above
  - how tech-affine are they (just feel though)
  - ask them for an example of the data they're working with (and you're potentially interested in visualizing)
    - aussen, boiler, puffer oben, puffer unten
    - physical values that we don't have data of
  - ask if they have created any charts or other tools for themselves - when talking to these people group them into UX persona afterwards to abstract all the information
    - haut z heizigsapp dings
  - Don't ask (never really helps..):
    - "what do you need"
    - "is this intuitive for you"
    - "do you like it"

- prototype
  - paper or figma, the interactivity requires a lot of work and should be done later
  - feedback is usually more valuable on something that looks like a prototype because the user doesn't feel the need to hold back
- get feedback how the tool is performing on a real world task
  - usability tests
    - book: rocket surgery made easy
    - watch people using your tool
    - ask them if this fits the process they are used to or if it helps them to make the decision
    - ask them to think aloud but do not talk yourself to not correct or influence them (you want unfiltered feedback and struggles)
    - record it or ask someone else to take notes if you can because asking them to do tasks is already very consuming
    - often new is uncomfortable because it's new
- iterate

Questions:

- What should better be automated and for what is it better to build a tool to assist with a decision
  - assist decision because there is no interface or possibility to automate the firing process
