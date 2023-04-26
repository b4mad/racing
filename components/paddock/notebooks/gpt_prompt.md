<class 'pandas.core.frame.DataFrame'>
Index: 39727 entries, 0 to 46871
Data columns (total 29 columns):
 #   Column               Non-Null Count  Dtype
---  ------               --------------  -----
 0   result               39727 non-null  object
 1   table                39727 non-null  int64
 2   _start               39727 non-null  datetime64[ns, tzlocal()]
 3   _stop                39727 non-null  datetime64[ns, tzlocal()]
 4   _time                39727 non-null  datetime64[ns, tzlocal()]
 5   CarModel             39727 non-null  object
 6   CurrentLap           39727 non-null  object
 7   GameName             39727 non-null  object
 8   SessionId            39727 non-null  object
 9   SessionTypeName      39727 non-null  object
 10  TrackCode            39727 non-null  object
 11  _measurement         39727 non-null  object
 12  host                 39727 non-null  object
 13  topic                39727 non-null  object
 14  user                 39727 non-null  object
 15  Brake                39727 non-null  float64
 16  Clutch               39727 non-null  float64
 17  CurrentLapIsValid    39727 non-null  bool
 18  CurrentLapTime       39727 non-null  float64
 19  DistanceRoundTrack   39727 non-null  float64
 20  Gear                 39727 non-null  float64
 21  Handbrake            39727 non-null  float64
 22  LapTimePrevious      39727 non-null  float64
 23  PreviousLapWasValid  39727 non-null  bool
 24  Rpms                 39727 non-null  float64
 25  SpeedMs              39727 non-null  float64
 26  SteeringAngle        39727 non-null  float64
 27  Throttle             39727 non-null  float64
 28  id                   39727 non-null  object
dtypes: bool(2), datetime64[ns, tzlocal()](3), float64(11), int64(1), object(12)
memory usage: 8.6+ MB



❯ pipenv run ./manage.py replay --session-id 1681021274
Loading .env environment variables...
 Replaying session 1681021274 as new session 1681553724
0                                                                                                                                                            2023-04-15 10:15:24,884 INFO Connected to telemetry.b4mad.racing
2023-04-15 10:15:24,884 DEBUG session_id: 1681021274, start: None, end: None, lap_numbers: None
 replay/crewchief/durandom/1681553724/iRacing/magnycours gp/Ferrari 488 GT3 Evo 2020/Practice
4410.0: LapTimePrevious: None -> -1.0
4410.0: CurrentLapIsValid: None -> False
4410.0: PreviousLapWasValid: None -> True
4410.0: CurrentLap: None -> 1
1.05723047: CurrentLapIsValid: False -> True
0.459159255: CurrentLap: 1 -> 2
170.977783: LapTimePrevious: -1.0 -> 100.818
971.45: CurrentLapIsValid: True -> False
0.216924369: CurrentLap: 2 -> 3
112.98333: LapTimePrevious: 100.818 -> -1.0
112.98333: CurrentLapIsValid: False -> True
112.98333: PreviousLapWasValid: True -> False
113.7913: PreviousLapWasValid: False -> True
0.236248091: CurrentLap: 3 -> 4
110.502083: LapTimePrevious: -1.0 -> 101.0466
0.0479498059: CurrentLap: 4 -> 5
222.921082: LapTimePrevious: 101.0466 -> 100.823
1.246441: CurrentLap: 5 -> 6
100.04921: LapTimePrevious: 100.823 -> 99.4026
2436.50513: CurrentLapIsValid: True -> False
0.688353658: CurrentLap: 6 -> 7
106.740479: LapTimePrevious: 99.4026 -> 107.9166
106.740479: CurrentLapIsValid: False -> True
106.740479: PreviousLapWasValid: True -> False
107.5471: PreviousLapWasValid: False -> True
1.3185463: CurrentLap: 7 -> 8
14.60126: CurrentLapIsValid: True -> False
94.30895: LapTimePrevious: 107.9166 -> 99.0674
94.30895: CurrentLapIsValid: False -> True
94.30895: PreviousLapWasValid: True -> False
95.0567856: PreviousLapWasValid: False -> True
2528.813: CurrentLapIsValid: True -> False
0.256659776: CurrentLap: 8 -> 9
121.161278: LapTimePrevious: 99.0674 -> -1.0
121.161278: CurrentLapIsValid: False -> True
121.161278: PreviousLapWasValid: True -> False
122.795441: PreviousLapWasValid: False -> True
941.8128: CurrentLapIsValid: True -> False
0.19759059: CurrentLap: 9 -> 10
183.139175: LapTimePrevious: -1.0 -> 101.7361
183.139175: CurrentLapIsValid: False -> True
183.139175: PreviousLapWasValid: True -> False
184.890244: PreviousLapWasValid: False -> True
1840.38562: CurrentLapIsValid: True -> False
133.5775

For this session
