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
    Plotly.newPlot(mapDiv, []);

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

        const telemetryLaps = [...new Set(data.data.map(item => item[lapIndex]))];
        telemetryLaps.sort((a, b) => a - b);

        const telemetryData = data.data.map(item => ({
            DistanceRoundTrack: item[distanceIndex],
            SpeedMs: item[speedIndex],
            Throttle: item[throttleIndex],
            CurrentLap: parseInt(item[lapIndex]),
            WorldPositionX: item[worldPositionXIndex],
            WorldPositionY: item[worldPositionYIndex],
            WorldPositionZ: item[worldPositionZIndex]
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

                if (mapDataAvailable) {
                    // Extract WorldPositionX and WorldPositionY from telemetry
                    const xValues = d.map(d => d.WorldPositionX);
                    const yValues = d.map(d => d.WorldPositionY);

                    // Create a 2D scatter plot with Plotly
                    const trace = {
                        x: xValues,
                        y: yValues,
                        mode: 'markers',
                        type: 'scatter',
                        name: 'Lap ' + lap,
                        'marker.color': 'red',
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
                const trace = speedGraphDiv.data[lap1index];
                // get the y value of the closest point to the selected distance
                // const yValue = trace.y[trace.x.indexOf(distance)];
                const yValue = trace.y[point.pointIndex];
                // set the speedValue1 to the y value
                speedValue1.innerHTML = yValue;
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
