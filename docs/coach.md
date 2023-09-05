# TrackGuide

## Recon Laps

### What to expect and learn

At slower pace, the car will be more stable and easier to control. You will be able to see the track better and learn the racing line. You will also be able to see the braking points and the apexes of the corners. You will be able to see the track better and learn the racing line. You will also be able to see the braking points and the apexes of the corners.

### How to do it

1. check speed to be always 20% below race pace
2. talk through corner
   1. Braking point
   2. Turn in
   3. Apex point / how much curb

E.g.

## Timed Laps

### What to expect and learn

We'll give you fewer instructions and you'll be able to drive at a faster pace.

### How to do it

Focus on these things. Only progress to the next one when you have mastered the previous one.

1. braking points
2. brake force
3. turn in


## A real coach

1. Advice just before the actionable moment
   e.g. "brake at the 100m mark", "turn in a bit earlier"

2. Feedback just after the actionable moment
   e.g. "you braked too late", "you braked too hard", "you braked too soft"

3. Realtime alerts
   e.g. "brake harder", "reduce speed", "brake"

The Coach knows if the adivce is important enough to be given.
He needs to compare all available advice and decide which one is the most important one.
He also needs to decide if the driver is ready for the advice.

If the driver is not ready, the advice will be given later.


* Let's drive some laps at a slow pace to get a feel for the track. [start of the session]
* Drive a bit slower [monitor speed, if speed is too high for too long]
* This is turn 1, brake at the 100m mark [at: brake_point]
* Brake 80 % [at]
* Turn in just before the marshals shack
* This lap was 20% slower than race pace, let's continue our recon laps []
* Ok, looks like you're ready for some timed laps [change of mode, due to increased speed]

1. Messages to be played during recon session
   * each message should be played once
   * if all messages have been played, start playing from the beginning
   * multiple messages can be played in a segment
   * no grading of the advice
2. Timed laps
   * focus on brake point, brake pressure, gear, turn_in, apex [hardcoded order, !!! need category field]
   * tell the driver that we're focusing on the brake points now
   * only proceed to the next once the first has a good score or doesnt show any improvement
   * give immediate feedback, like "that was a little to late"

### One large "TrackGuide App"
* get instantiated by coach
* knows all segments, all notes (CSV),
* similar to history, get's notified on every tick
* Can be shown to future app developers

# Coach knows what is to being played

We send when a message is to be played (at - max_at) and we know how long it takes for a message to finish.
~~Keep track of the time once a message should be triggered and when it's done.~~
Only send messages that dont overlap.

1. message.response_hot_lap(at_meters) -> response_object
   1. keep message reference
   2. if message is marked as sent or discarded, we know about it
2. if coach sends message, mark message as sent
3. if message needs to be discarded (reset to pit, or overlap with other message)
   1. mark as discarded

### Components to be implemented

1. Monitor
   monitors one specific aspect, not bound to segments, e.g. speed should be below 80%

2. Strategy


* get's called every meter on the track to check if it's applicable now


