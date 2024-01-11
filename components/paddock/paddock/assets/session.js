document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const speedGraphDiv = document.getElementById('speed-graph');
    const throttleGraphDiv = document.getElementById('throttle-graph');
    const lapSelector1 = document.getElementById('lap-selector-1');
    const lapSelector2 = document.getElementById('lap-selector-2');
    var lap1index = 0;
    var lap2index = 0;
    const mapDiv = document.getElementById('map');
    const speedValue1 = document.getElementById('speed-value-1');
    const speedValue2 = document.getElementById('speed-value-2');

    // Initial Telemetry Data
    let telemetry = [];
    let laps = [];

    var mapDataAvailable = false;

    // get the session_id from the url
    const url = new URL(window.location.href);
    // the session id is the last part of the url
    const session_id = url.pathname.split('/').pop();

    // Create empty plots
    var layout = {
        height: 200, // Shorter height to make the graph similar to the one in the screenshot
        xaxis: {
        //   title: 'Distance/Time',
          showgrid: true,
          zeroline: false,
          gridcolor: '#E2E2E2'
        },
        yaxis: {
        //   title: 'Speed (km/h)',
          showline: false,
          gridcolor: '#E2E2E2'
        },
        margin: {
          l: 50,
          r: 50,
          b: 50,
          t: 50,
          pad: 4
        },
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff'
      };

    Plotly.newPlot(speedGraphDiv, [], layout);
    Plotly.newPlot(throttleGraphDiv, [], layout);

    // the map layout is the same, but without coordinates
    mapLayout = {
        // height and width are the same
        height: '100%',
        xaxis: {
            showgrid: true,
            zeroline: false,
            gridcolor: '#E2E2E2',
            aspectratio: '1:1'
        },
        yaxis: {
            showline: false,
            gridcolor: '#E2E2E2',
            aspectratio: '1:1'
        },
        margin: {
            l: 50,
            r: 50,
            b: 50,
            t: 50,
            pad: 4
        },
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff'
    };
    Plotly.newPlot(mapDiv, [], mapLayout);

    const graphDivs = [speedGraphDiv, throttleGraphDiv];
    const hoverCallback = function(data) {
        updateDistance(data.points[0]);
    }
    const relayoutCallback = function(eventdata, targetDiv) {
        if (eventdata['xaxis.range[0]'] && eventdata['xaxis.range[1]']) {
            Plotly.relayout(targetDiv, {
                'xaxis.range[0]': eventdata['xaxis.range[0]'],
                'xaxis.range[1]': eventdata['xaxis.range[1]']
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

    speedGraphDiv.on('plotly_relayout', function(eventdata) {
        relayoutCallback(eventdata, throttleGraphDiv);
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
            SpeedMs: item[speedIndex],
            Throttle: item[throttleIndex],
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
        }

        return { telemetryLaps, telemetryData };
    }



    // Fetch Data from Django and Initialize Graphs
    fetch('/api/session/' + session_id)
        .then(response => response.json())
        .then(data => {
            const { telemetryLaps, telemetryData } = parseTelemetryData(data);
            laps = telemetryLaps;
            laps.forEach(lap => {
                telemetry[lap] = telemetryData.filter(item => item.CurrentLap === lap);
            });

            // Populate lap selector options
            // add an option for all laps
            const option = document.createElement('option');
            option.value = 'all';
            option.text = 'All Laps';
            option.selected = true;
            lapSelector1.appendChild(option);

            // add a none option to the second lap selector
            const option2 = document.createElement('option');
            option2.value = 'none';
            option2.text = 'None';
            option2.selected = true;
            lapSelector2.appendChild(option2);

            // Assuming `laps` is an array of your laps
            laps.forEach((lap, index) => {
                const option1 = document.createElement('option');
                option1.value = index;
                option1.text = `Lap ${index + 1}`;
                lapSelector1.appendChild(option1);

                const option2 = option1.cloneNode(true);
                lapSelector2.appendChild(option2);
            });
            // laps.forEach(lap => {
            //     const option = document.createElement('option');
            //     option.value = lap;
            //     option.text = `Lap ${lap}`;
            //     lapSelector.appendChild(option);
            // });

            laps.forEach((lap, index) => {
                // Store the mapping of lap to trace index

                d = telemetry[lap];
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

                if (mapDataAvailable && index === 0) {
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
            });

            updateLap();
        });

        function updateLap() {
            // if the selected lap is 'all', show all traces
            if (lapSelector1.value === 'all') {
                for (let i = 0; i < laps.length; i++) {
                    Plotly.restyle(speedGraphDiv, 'visible', true, i);
                    Plotly.restyle(throttleGraphDiv, 'visible', true, i);
                }
                lap1index = 0;
                lap2index = 0;
                return;
            }

            // hide all traces
            for (let i = 0; i < laps.length; i++) {
                Plotly.restyle(speedGraphDiv, 'visible', false, i);
                Plotly.restyle(throttleGraphDiv, 'visible', false, i);
            }

            lap1index = parseInt(lapSelector1.value);
            // show only the selected lap using the mapping
            Plotly.restyle(speedGraphDiv, 'visible', true, lap1index);
            Plotly.restyle(throttleGraphDiv, 'visible', true, lap1index);

            // if the selected lap is 'none'
            if (lapSelector2.value !== 'none') {
                lap2index = parseInt(lapSelector2.value);
                Plotly.restyle(speedGraphDiv, 'visible', true, lap2index);
                Plotly.restyle(throttleGraphDiv, 'visible', true, lap2index);
            }


        }

        function updateDistance(point) {
            distance = point.x;

            // Update vertical line
            Plotly.relayout(speedGraphDiv, {
                shapes: [
                    {
                        type: 'line',
                        x0: distance,
                        x1: distance,
                        y0: 0,
                        y1: 1,
                        xref: 'x',
                        yref: 'paper',
                        line: { color: 'red' }
                    }
                ]
            });

            Plotly.relayout(throttleGraphDiv, {
                shapes: [
                    {
                        type: 'line',
                        x0: distance,
                        x1: distance,
                        y0: 0,
                        y1: 1,
                        xref: 'x',
                        yref: 'paper',
                        line: { color: 'red' }
                    }
                ]
            });

            if (point.curveNumber === lap1index) {
                // set speedValue1 to the speed at the selected distance
                // get the closest telemetry item to the selected distance
                // get the first trace from the speed graph
                trace = speedGraphDiv.data[lap1index];
                // get the y value of the closest point to the selected distance
                // const yValue = trace.y[trace.x.indexOf(distance)];
                const yValue = trace.y[point.pointIndex];
                // set the speedValue1 to the y value
                speedValue1.innerHTML = yValue;

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
            if (point.curveNumber === lap2index) {
                // set speedValue1 to the speed at the selected distance
                // get the closest telemetry item to the selected distance
                // get the first trace from the speed graph
                const trace = speedGraphDiv.data[lap2index];
                // get the y value of the closest point to the selected distance
                // const yValue = trace.y[trace.x.indexOf(distance)];
                const yValue = trace.y[point.pointIndex];
                // set the speedValue1 to the y value
                speedValue2.innerHTML = yValue;
            }

        }



    // Event Listeners
    lapSelector1.addEventListener('change', updateLap);
    lapSelector2.addEventListener('change', updateLap);
    // distanceSlider.addEventListener('input', updateDistance);
});
