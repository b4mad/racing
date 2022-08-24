# Simracing lap comparison

We want to measure the difference of two laps on a simracing circuit. The function should indicate what how input features differes at a trackposition, such as throttle or brake inputs.
See the added [AI_Coaching](AI_Coaching.pdf) document.

## Acceptance criteria

- JupyterNotebook in python
- data set is split into laps - pandas dataframe
- select one lap as expert lap C(s) and one lap as student lap S(s)
- for each Throttle, Brake and SpeedKmh, draw a graph of C(s) and S(s) over TrackPositionPercent (3 graphs with 2 lines each)
- function D that is initialized with C(s) lap data
- function D takes S(s) as input - with Throttle, Brake, SpeedKmh as features and TrackPositionPercent as 's' and calculates a normalized  difference for the combination of all features
- rank each feature by the size of their respective differences
- for each Throttle, Brake and SpeedKmh, draw a graph of C(s) and S(s) and difference from function D over TrackPositionPercent (3 graphs with 3 lines each)

## resources

The csv file contains laps on zandvoort grandprix. Some data, not all, is visualized at https://pitwall.b4mad.racing/d/oPyrx7lnz/b4mad-racing-details?orgId=1&var-SessionId=89db51de-22a6-4033-8201-2fc37a5fe905&from=1652010217251&to=1652013039231

## function suggestions

For the function aspect, something like (we can add annotations for types or let the implementer decide):

```
def featurize(trajectory):
    '''Compute derived metrics at each time-step e.g. rate of change of steering, acceleration etc.'''
    return new_trajectory

def compute_s(trajectory):
    '''Map trajectory based on time to trajectory based on s i.e. the distance covered along the center line'''
    return new_trajectory

def metric(student_features, coach_features):
    ''''Compare student and coach features at fixed s'''
    return distance

def compare(student, coach):
    ''''Compare student and coach features at each s and return ranked list''''
    return ranked_list/dict

def suggest(ranked_list):
    '''Go over ranked list (in decreasing order of distance between student and coach)
     and make suggestions in natural language'''
    return {'s1': 'brake now and aim for apex', 's2': '', ...}

def run(student, coach):
    '''Put everything together'''
    student = compute_s(featurize(student))
    coach = compute_s(featurize(coach))

   ranked = compare(student, coach)
```