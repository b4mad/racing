# Driving style changes

Implementation of a change should result in an improvement of lap time.
Changes can be compared by the amount of lap time, or sector time, improvement.

Time improvement should be measured over the course of one or multiple corners.

If there is one corner between two straights, the time measurement would start
at the braking zone and end at the acceleration zone. Or the corner entry and exit.
One might factor entry speed and exit speed into the measurement, since it's not
only the time spend driving through a corner, but the overall lap time what matters.

A more complex scenario might be the combination of successive corners, such as a chicane,
which is usually a left followed by a right, or vice versa.

## Braking point
You brake too early or too late
Input: track position percent, brake input

## Trail braking
Instead of releasing the brake apprubtly, you ease off the brakes while turning the car into a corner.
Input: rate of change of brake input

## Acceleration
Instead of going full on the throttle, you ease into the throttle.
Input: rate of change of throttle input

## Overlapping brake and throttle

## Grip
Having the tires not at full grip, i.e. either you are too slow or turning to slow and the tires still have grip available or you are braking too hard or accelerating too much and the tires either block or lose grip.

## Racing line
Not following the racing line
Input: track position x,y



## Reinforcement learning
We have human driver telemetry data as input and car telemetry data and world positions as output.
The function to be maximised is corner time, sector time and lap time.
The agent inputs are the car telemetry data and the world positions.
The agent outputs are human driver inputs to the car, such as throttle, brake and steering.
The world reaction are the car telemetry data, such as tire grip and speed and the world positions, such as percent of track completed.


Q: would the agent learn the best combination of all laps used to train the agent? I.e. would we get a better lap than a human selected coach lap?

Q: would we get an agent model that would respond with the best next car input given a current world and car telemetry?



## AI Coaching

The coach should provide the driver with actionable advice on how to improve the lap time.
Therefore the coach needs to evaluate what changes have the biggest impact on the lap time.
This could be posed as a ranking problem.

Given a corner inputs, find a recorded corner that is different in only one feature and compare the time improvement.
Do this for all available features and select the one with the biggest improvement.
https://towardsdatascience.com/time-series-clustering-deriving-trends-and-archetypes-from-sequential-data-bb87783312b4

1. identify which cluster you belong to
2. find adjacent clusters


It also needs to evaluate past behaviour and incorporate changes the driver has made.
E.g. if you usually brake too early in your previous laps, but now you fixed that behaviour, the coach should not notify you about that anymore.
So the coach needs to have some memory of some sorts.


## Braking coach

Given a position on the track, the coach should notify the driver to brake in 100m, 50m and now.

The model is trained to emit a braking point signal 100m, 50m and now for the given position.
The model should have some memory for the previous inferences, since we dont know about the frequency of inference, we can only assume that the previous inference is position wise before the current inference.