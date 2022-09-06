# Braking zone detection and AI classification on braking points

We collect a number of sim racing telemetry data in an InfluxDB database.
The data is stored in the `racing` bucket and the measurement is `laps`.

## Flux queries

see [influx_query_sample](../analysis/src/influx_query_sample.ipynb) notebook for
example queries.

## Braking zone detection

For all laps on TrackCode `SpaFrancorchamps-Spa_Francorchamps_2022` and CarModel `Formula Trainer`
identify the braking zone.
The braking zone is the position `TrackPositionPercent` when most cars on average start braking.

1. This should result in a number of distinct braking zones on the [track](https://en.wikipedia.org/wiki/Circuit_de_Spa-Francorchamps#/media/File:Spa-Francorchamps_of_Belgium.svg)
2. Translate the `TrackPositionPercent` to a meter position given the length of the track: 7.004 km
3. Plot the braking zone position on the track in a graph, with x axis as the track position and y axis as the braking zone.

## AI classification

Train a sci-kit learn model to predict braking points.

The model is trained to emit a braking point signal at 100m, 50m and now for the given position.
The model should have some memory for the previous inferences, since we dont know about the frequency of inference, we can only assume that the previous inference is position wise before the current inference.

```
f(position_current, positions_previous, TrackCode, CarModel) -> (braking_point_100m, braking_point_50m, braking_point_now)
```

The model classifies a binary vector of length 3, where the first element is the braking point is at 100m
distance from the positions_current, the second element is true when the braking point at 50m distance from now and the third element is 1 if the braking point is at the current position.

The model should be trained on a training subset of the data collected from all laps, with the labeled data being the calculated braking points from the 'Braking zone detection' section. The model should also be trained on artifical data, where the position is an increasing number.

1. Test the model with a testing subset of the data collected from all laps. The model should predict exactly N*3 braking points detected from the previous section.
