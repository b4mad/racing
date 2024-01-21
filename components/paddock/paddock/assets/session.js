document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const timeGraphDiv = document.getElementById('time-graph');
    const speedGraphDiv = document.getElementById('speed-graph');
    const throttleGraphDiv = document.getElementById('throttle-graph');
    const brakeGraphDiv = document.getElementById('brake-graph');
    const gearGraphDiv = document.getElementById('gear-graph');
    const steerGraphDiv = document.getElementById('steer-graph');
    const graphDivs = [timeGraphDiv, speedGraphDiv, throttleGraphDiv, brakeGraphDiv, gearGraphDiv, steerGraphDiv];

    const lapSelector1 = document.getElementById('lap-selector-1');
    const lapSelector2 = document.getElementById('lap-selector-2');
    var lap1index = 0;
    var lap2index = 0;
    const mapDiv = document.getElementById('map');
    const mapCol = document.getElementById('col-map');
    const graphsCol = document.getElementById('col-graphs');
    // const speedValue1 = document.getElementById('speed-value-1');
    // const speedValue2 = document.getElementById('speed-value-2');
    const loadingSpinner = document.getElementById('loading-spinner');

    // Initial Telemetry Data
    let telemetry = [];
    let laps = [];
    let lapsToGraphIndex = {};

    var mapDataAvailable = false;

    // get the session_id from the url
    const url = new URL(window.location.href);
    // the session id is the last part of the url
    path_parts = url.pathname.split('/');
    const lap_numer = parseInt(path_parts.pop());
    const session_id = path_parts.pop();

    // Create empty plots
    const layout_base = {
        height: 100,
        xaxis: {
            // title: 'Distance/Time',
            showgrid: true,
            zeroline: false,
            gridcolor: '#E2E2E2',
            side: 'top', // Add this line to position x-axis at the top
            fixedrange: true, // disable zoom
        },
        yaxis: {
            // title: 'km/h',
            showline: false,
            gridcolor: '#E2E2E2',
            fixedrange: true, // disable zoom
        },
        margin: {
            l: 50,
            r: 0,
            b: 10,
            t: 5,
            pad: 4
        },
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff'
    };
    // make a deep copy of the layout
    var layout = JSON.parse(JSON.stringify(layout_base));
    layout.yaxis.fixedrange = false;
    layout.xaxis.fixedrange = false;
    layout.margin.t = 50;
    layout.height += 50;
    layout.yaxis.title = 'time';
    Plotly.newPlot(timeGraphDiv, [], layout);

    // make a deep copy of the layout
    layout = JSON.parse(JSON.stringify(layout_base));
    layout.yaxis.title = 'km/h';
    Plotly.newPlot(speedGraphDiv, [], layout, {displayModeBar: false});

    // make a deep copy of the layout
    layout = JSON.parse(JSON.stringify(layout_base));
    layout.yaxis.title = 'throttle';
    Plotly.newPlot(throttleGraphDiv, [], layout, {displayModeBar: false});

    // make a deep copy of the layout
    layout = JSON.parse(JSON.stringify(layout_base));
    layout.yaxis.title = 'brake';
    Plotly.newPlot(brakeGraphDiv, [], layout, {displayModeBar: false});

    // make a deep copy of the layout
    layout = JSON.parse(JSON.stringify(layout_base));
    layout.yaxis.title = 'gear';
    Plotly.newPlot(gearGraphDiv, [], layout, {displayModeBar: false});

    // make a deep copy of the layout
    layout = JSON.parse(JSON.stringify(layout_base));
    layout.yaxis.title = 'steer';
    Plotly.newPlot(steerGraphDiv, [], layout, {displayModeBar: false});


    // the map layout is the same, but without coordinates
    mapLayout = {
        // height and width are the same
        height: '100%',
        xaxis: {
            showgrid: false,
            showline: false,
            zeroline: false,
            visible: false
        },
        yaxis: {
            showgrid: false,
            showline: false,
            zeroline: false,
            visible: false
        },
        margin: {
            l: 20,
            r: 20,
            b: 20,
            t: 20,
            pad: 4
        },
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff'
    };
    Plotly.newPlot(mapDiv, [], mapLayout);

    const hoverCallback = function(data) {
        updateDistance(data.points[0]);
    }
    const relayoutCallback = function(eventdata) {
        if (eventdata['xaxis.range[0]'] && eventdata['xaxis.range[1]']) {
            graphDivs.forEach(graphDiv => {
                if (graphDiv === timeGraphDiv) {
                    return;
                }
                Plotly.relayout(graphDiv, {
                    'xaxis.range[0]': eventdata['xaxis.range[0]'],
                    'xaxis.range[1]': eventdata['xaxis.range[1]']
                });
            });

            const trace = speedGraphDiv.data[0];
            const minDistance = eventdata['xaxis.range[0]'];
            const maxDistance = eventdata['xaxis.range[1]'];
            // find the first point where the distance is greater than the minDistance
            const maxIndex = trace.x.findIndex(x => x > maxDistance);
            const minIndex = trace.x.findIndex(x => x > minDistance);

            const mapTrace = mapDiv.data[0];
            // in mapTrace, iterate from minIndex to maxIndex and find the smallest and largest x and y values
            let smallestX = mapTrace.x[minIndex];
            let largestX = mapTrace.x[minIndex];
            let smallestY = mapTrace.y[minIndex];
            let largestY = mapTrace.y[minIndex];

            for (let i = minIndex; i <= maxIndex; i++) {
                const x = mapTrace.x[i];
                const y = mapTrace.y[i];
                if (x < smallestX) {
                    smallestX = x;
                }
                if (x > largestX) {
                    largestX = x;
                }
                if (y < smallestY) {
                    smallestY = y;
                }
                if (y > largestY) {
                    largestY = y;
                }
            }

            const margin = 50;
            Plotly.relayout(mapDiv, {
                'xaxis.range[0]': smallestX - margin,
                'xaxis.range[1]': largestX + margin,
                'yaxis.range[0]': smallestY - margin,
                'yaxis.range[1]': largestY + margin,
            });
        }
    }

    graphDivs.forEach(graphDiv => {
        graphDiv.on('plotly_hover', hoverCallback);
    });

    timeGraphDiv.on('plotly_relayout', function(eventdata) {
        relayoutCallback(eventdata);
    });
    // FIXME this leads to a recursion
    // throttleGraphDiv.on('plotly_relayout', function(eventdata) {
    //     relayoutCallback(eventdata, throttleGraphDiv);
    // });


    function parseTelemetryData(data) {
        // Get column indexes
        const distanceIndex = data.columns.indexOf('DistanceRoundTrack');
        const speedIndex = data.columns.indexOf('SpeedMs');
        const throttleIndex = data.columns.indexOf('Throttle');
        const brakeIndex = data.columns.indexOf('Brake');
        const gearIndex = data.columns.indexOf('Gear');
        const steerIndex = data.columns.indexOf('SteeringAngle');
        const currentLapTime = data.columns.indexOf('CurrentLapTime');
        const lapIndex = data.columns.indexOf('CurrentLap');
        const worldPositionXIndex = data.columns.indexOf('WorldPosition_x');
        const worldPositionYIndex = data.columns.indexOf('WorldPosition_y');
        const worldPositionZIndex = data.columns.indexOf('WorldPosition_z');
        const yawIndex = data.columns.indexOf('Yaw');
        const pitchIndex = data.columns.indexOf('Pitch');
        const rollIndex = data.columns.indexOf('Roll');

        const telemetryLaps = [...new Set(data.data.map(item => item[lapIndex]))];
        telemetryLaps.sort((a, b) => a - b);

        const telemetryData = data.data.map(item => ({
            DistanceRoundTrack: item[distanceIndex],
            SpeedMs: Math.round(item[speedIndex] * 3.6),
            Throttle: Math.round(item[throttleIndex] * 100),
            Brake: Math.round(item[brakeIndex] * 100),
            Gear: item[gearIndex],
            SteeringAngle: item[steerIndex],
            CurrentLapTime: item[currentLapTime],
            CurrentLap: parseInt(item[lapIndex]),
            WorldPositionX: item[worldPositionXIndex],
            WorldPositionY: item[worldPositionYIndex],
            WorldPositionZ: item[worldPositionZIndex],
            Yaw: item[yawIndex],
            Pitch: item[pitchIndex],
            Roll: item[rollIndex],
        }));

        if (worldPositionXIndex !== -1 && worldPositionYIndex !== -1 && worldPositionZIndex !== -1) {
            mapDataAvailable = true;
            // // show the map
            // mapCol.classList.remove('d-none');
            // graphsCol.classList.remove('col-12');
            // graphsCol.classList.add('col-8');
        } else {
            mapDataAvailable = false;
            // // hide the map
            // mapCol.classList.add('d-none');
            // graphsCol.classList.remove('col-8');
            // graphsCol.classList.add('col-12');
        }

        return { telemetryLaps, telemetryData };
    }



    // Fetch Data from Django and Initialize Graphs
    fetch('/api/session/' + session_id)
    .then(response => response.json())
    .then(data => {
        loadingSpinner.classList.add('d-none');
        const { telemetryLaps, telemetryData } = parseTelemetryData(data);
        laps = telemetryLaps;
        laps.forEach(lap => {
            telemetry[lap] = telemetryData.filter(item => item.CurrentLap === lap);
        });

        lap = lapSelector1.value;
        showLap(lap);
    });

    function showLap(lap) {
        lap = parseInt(lap);
        // check if lap is in the telemetry array
        if (telemetry[lap] === undefined) {
            return;
        }

        // get the index of the lap in the laps array
        const graphIndex = lapsToGraphIndex[lap];

        // check if the lap is in the trace array
        if (graphIndex !== undefined) {
            // just show the trace
            graphDivs.forEach(graphDiv => {
                Plotly.restyle(graphDiv, 'visible', true, graphIndex);
            });

            if (mapDataAvailable) {
                Plotly.restyle(mapDiv, 'visible', true, graphIndex);
            }
            return;
        }

        // get data for the selected lap
        const d = telemetry[lap];
        lapsToGraphIndex[lap] = speedGraphDiv.data.length;

        timeTrace = {
            x: d.map(t => t.DistanceRoundTrack),
            y: d.map(t => t.CurrentLapTime),
            mode: 'lines',
            name: 'Lap ' + lap,
            line: {
                // dash: 'dash', // Dashed line for the data points
                // color: 'blue'
            }
            // 'marker.color': 'red',
        };
        Plotly.addTraces(timeGraphDiv, timeTrace);

        speedTrace = {
            x: d.map(t => t.DistanceRoundTrack),
            y: d.map(t => t.SpeedMs),
            mode: 'lines',
            name: 'Lap ' + lap,
            line: {
                // dash: 'dash', // Dashed line for the data points
                // color: 'blue'
            }
            // 'marker.color': 'red',

        };
        Plotly.addTraces(speedGraphDiv, speedTrace);

        throttleTrace = {
            x: d.map(t => t.DistanceRoundTrack),
            y: d.map(t => t.Throttle),
            mode: 'lines',
            name: 'Lap ' + lap,
            'marker.color': 'red',
        };
        Plotly.addTraces(throttleGraphDiv, throttleTrace);

        brakeTrace = {
            x: d.map(t => t.DistanceRoundTrack),
            y: d.map(t => t.Brake),
            mode: 'lines',
            name: 'Lap ' + lap,
            'marker.color': 'red',
        };
        Plotly.addTraces(brakeGraphDiv, brakeTrace);

        gearTrace = {
            x: d.map(t => t.DistanceRoundTrack),
            y: d.map(t => t.Gear),
            mode: 'lines',
            name: 'Lap ' + lap,
            'marker.color': 'red',
        };
        Plotly.addTraces(gearGraphDiv, gearTrace);

        steerTrace = {
            x: d.map(t => t.DistanceRoundTrack),
            y: d.map(t => t.SteeringAngle),
            mode: 'lines',
            name: 'Lap ' + lap,
            'marker.color': 'red',
        };
        Plotly.addTraces(steerGraphDiv, steerTrace);

        if (mapDataAvailable) {
            // Extract WorldPositionX and WorldPositionY from telemetry
            const xValues = d.map(d => d.WorldPositionX);
            const yValues = d.map(d => d.WorldPositionY);

            // Create a 2D scatter plot with Plotly
            const trace = {
                x: xValues,
                y: yValues,
                yaw: d.map(d => d.Yaw),
                pitch: d.map(d => d.Pitch),
                roll: d.map(d => d.Roll),
                mode: 'lines',
                line: {},
            };
            Plotly.addTraces(mapDiv, trace);
        }
    }

    function updateLap() {
        // hide all traces
        for (let i = 0; i < speedGraphDiv.data.length; i++) {
            graphDivs.forEach(graphDiv => {
                Plotly.restyle(graphDiv, 'visible', false, i);
            });
            if (mapDataAvailable) {
                Plotly.restyle(mapDiv, 'visible', false, i);
            }
        }

        [parseInt(lapSelector1.value), parseInt(lapSelector2.value)].forEach(lap => {
            // check if lap is in the telemetry array

            if (telemetry[lap] === undefined) {
                loadingSpinner.classList.remove('d-none');
                // get the data for the selected lap
                fetch('/api/lap/' + lap)
                .then(response => response.json())
                .then(data => {
                    loadingSpinner.classList.add('d-none');
                    if (data.data.length === 0) {
                        alert('No data for lap ' + lap);
                        return;
                    }
                    const { telemetryLaps, telemetryData } = parseTelemetryData(data);
                    // telemetry[lap] = telemetryData[0].filter(item => item.CurrentLap === lap);
                    telemetry[lap] = telemetryData;
                    showLap(lap);
                });
            } else {
                showLap(lap);
            }
        });
    }

    function updateDistance(point) {
        distance = point.x;

        const line = {
            type: 'line',
            x0: distance,
            x1: distance,
            y0: 0,
            y1: 1,
            xref: 'x',
            yref: 'paper',
            line: { color: 'red' }
        };
        // Update vertical line
        graphDivs.forEach(graphDiv => {
            Plotly.relayout(graphDiv, {shapes: [ line ]});
        });


        if (point.curveNumber === lap1index) {
            // set speedValue1 to the speed at the selected distance
            // get the closest telemetry item to the selected distance
            // get the first trace from the speed graph
            trace = speedGraphDiv.data[lap1index];
            // get the y value of the closest point to the selected distance
            // const yValue = trace.y[point.pointIndex];
            // set the speedValue1 to the y value
            // speedValue1.innerHTML = yValue;

            // highlight the closest point on the map
            if (mapDataAvailable) {
                // draw a circle at the x, y position of the closest point
                trace = mapDiv.data[0];
                const circleSize = 20;
                const circle = {
                    type: 'circle',
                    xref: 'x',
                    yref: 'y',
                    x0: trace.x[point.pointIndex] - circleSize,
                    y0: trace.y[point.pointIndex] - circleSize,
                    x1: trace.x[point.pointIndex] + circleSize,
                    y1: trace.y[point.pointIndex] + circleSize,
                    line: { color: 'red' }
                };

                // add an arrow to the circle, pointing in the direction of the yaw
                // Convert degrees to radians
                function degreesToRadians(degrees) {
                    return degrees * (Math.PI / 180);
                }

                const arrowLength = 100;
                const arrow = {
                    type: 'line',
                    x0: trace.x[point.pointIndex],
                    y0: trace.y[point.pointIndex],
                    x1: trace.x[point.pointIndex] + Math.cos(degreesToRadians(trace.yaw[point.pointIndex])) * arrowLength,
                    y1: trace.y[point.pointIndex] + Math.sin(degreesToRadians(trace.yaw[point.pointIndex])) * arrowLength,
                    line: { color: 'green' }
                };
                // console.log(trace.yaw[point.pointIndex]);

                Plotly.relayout(mapDiv, {
                    shapes: [
                        circle,
                        arrow
                    ]
                });
            }
        }
        // if (point.curveNumber === lap2index) {
        //     // set speedValue1 to the speed at the selected distance
        //     // get the closest telemetry item to the selected distance
        //     // get the first trace from the speed graph
        //     const trace = speedGraphDiv.data[lap2index];
        //     // get the y value of the closest point to the selected distance
        //     // const yValue = trace.y[trace.x.indexOf(distance)];
        //     const yValue = trace.y[point.pointIndex];
        //     // set the speedValue1 to the y value
        //     speedValue2.innerHTML = yValue;
        // }

    }



    // Event Listeners
    lapSelector1.addEventListener('change', updateLap);
    lapSelector2.addEventListener('change', updateLap);
    // distanceSlider.addEventListener('input', updateDistance);
});
