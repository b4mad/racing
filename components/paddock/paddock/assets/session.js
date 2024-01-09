document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const speedGraphDiv = document.getElementById('speed-graph');
    const throttleGraphDiv = document.getElementById('throttle-graph');
    const lapSelector = document.getElementById('lap-selector');
    const distanceSlider = document.getElementById('distance-slider');
    const mapDiv = document.getElementById('map');

    // Initial Telemetry Data
    let telemetry = [];
    let laps = [];

    // get the session_id from the url
    const url = new URL(window.location.href);
    // the session id is the last part of the url
    const session_id = url.pathname.split('/').pop();

    // Create empty plots
    Plotly.newPlot(speedGraphDiv, []);
    Plotly.newPlot(throttleGraphDiv, []);

    // Fetch Data from Django and Initialize Graphs
    fetch('/api/session/' + session_id)
        .then(response => response.json())
        .then(data => {
            // Get column indexes
            const distanceIndex = data.columns.indexOf('DistanceRoundTrack');
            const speedIndex = data.columns.indexOf('SpeedMs');
            const throttleIndex = data.columns.indexOf('Throttle');
            const lapIndex = data.columns.indexOf('CurrentLap');
            const worldPositionXIndex = data.columns.indexOf('WorldPosition_x');
            const worldPositionYIndex = data.columns.indexOf('WorldPosition_y');
            const worldPositionZIndex = data.columns.indexOf('WorldPosition_z');

            laps = [...new Set(data.data.map(item => item[lapIndex]))];
            laps.sort((a, b) => a - b);

            telemetry_data = data.data.map(item => ({
                DistanceRoundTrack: item[distanceIndex],
                SpeedMs: item[speedIndex],
                Throttle: item[throttleIndex],
                CurrentLap: parseInt(item[lapIndex]),
                WorldPositionX: item[worldPositionXIndex],
                WorldPositionY: item[worldPositionYIndex],
                WorldPositionZ: item[worldPositionZIndex]
            }));
            // order the telemetry data by distance
            // telemetry_data.sort((a, b) => a.DistanceRoundTrack - b.DistanceRoundTrack);


            laps.forEach(lap => {
                telemetry[lap] = telemetry_data.filter(item => item.CurrentLap === lap);
            });

            // Populate lap selector options
            // add an option for all laps
            const option = document.createElement('option');
            option.value = 'all';
            option.text = 'All Laps';
            option.selected = true;
            lapSelector.appendChild(option);
            laps.forEach(lap => {
                const option = document.createElement('option');
                option.value = lap;
                option.text = `Lap ${lap}`;
                lapSelector.appendChild(option);
            });

            laps.forEach(lap => {
                d = telemetry[lap];
                speedTrace = {
                    x: d.map(t => t.DistanceRoundTrack),
                    y: d.map(t => t.SpeedMs),
                    mode: 'lines',
                    name: 'Lap ' + lap,
                    'marker.color': 'red',

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
            });

            // Extract WorldPositionX and WorldPositionY from telemetry
            const xValues = telemetry.map(d => d.WorldPositionX);
            const yValues = telemetry.map(d => d.WorldPositionY);

            // Create a 2D scatter plot with Plotly
            const trace = {
                x: xValues,
                y: yValues,
                mode: 'markers',
                type: 'scatter'
            };

            const layout = {autosize: true, title: '2D Map of Points'};
            if (worldPositionXIndex !== -1 && worldPositionYIndex !== -1) {
                Plotly.newPlot(mapDiv, [trace], layout);
            }

            updateLap();
            updateDistance();
        });

        function updateLap() {
            // if the selected lap is 'all', show all traces
            if (lapSelector.value === 'all') {
                for (let i = 0; i < laps.length; i++) {
                    Plotly.restyle(speedGraphDiv, 'visible', true, i);
                    Plotly.restyle(throttleGraphDiv, 'visible', true, i);
                }
                return;
            }

            const selectedLap = parseInt(lapSelector.value);

            // Filter data for the selected lap
            // const filteredTelemetry = telemetry.filter(item => item.CurrentLap === selectedLap);
            const filteredTelemetry = telemetry[selectedLap];

            // hide all traces except the selected lap
            for (let i = 0; i < laps.length; i++) {
                if (laps[i] === selectedLap) {
                    Plotly.restyle(speedGraphDiv, 'visible', true, i);
                    Plotly.restyle(throttleGraphDiv, 'visible', true, i);
                } else {
                    Plotly.restyle(speedGraphDiv, 'visible', false, i);
                    Plotly.restyle(throttleGraphDiv, 'visible', false, i);
                }
            }

            // set the min and max values of the distance slider
            distanceSlider.min = filteredTelemetry[0].DistanceRoundTrack;
            distanceSlider.max = filteredTelemetry[filteredTelemetry.length - 1].DistanceRoundTrack;

        }

        function updateDistance() {
            const selectedDistance = distanceSlider.value;

            // Update vertical line
            Plotly.relayout(speedGraphDiv, {
                shapes: [
                    {
                        type: 'line',
                        x0: selectedDistance,
                        x1: selectedDistance,
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
                        x0: selectedDistance,
                        x1: selectedDistance,
                        y0: 0,
                        y1: 1,
                        xref: 'x',
                        yref: 'paper',
                        line: { color: 'red' }
                    }
                ]
            });

    }

    // Event Listeners
    lapSelector.addEventListener('change', updateLap);
    distanceSlider.addEventListener('input', updateDistance);
});
