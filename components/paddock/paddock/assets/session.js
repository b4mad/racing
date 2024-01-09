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

            // Assuming data is an array of arrays with the relevant fields
            telemetry = data.data.map(item => ({
                DistanceRoundTrack: item[distanceIndex],
                SpeedMs: item[speedIndex],
                Throttle: item[throttleIndex],
                CurrentLap: parseInt(item[lapIndex]),
                WorldPositionX: item[worldPositionXIndex],
                WorldPositionY: item[worldPositionYIndex],
                WorldPositionZ: item[worldPositionZIndex]
            }));
            laps = [...new Set(data.data.map(item => item[lapIndex]))];

            // order laps
            laps.sort((a, b) => a - b);

            // Populate lap selector options
            laps.forEach(lap => {
                const option = document.createElement('option');
                option.value = lap;
                option.text = `Lap ${lap}`;
                // if it's the first lap, select it
                if (lap === laps[0]) {
                    option.selected = true;
                }
                lapSelector.appendChild(option);
            });

            // order the telemetry data by distance
            telemetry.sort((a, b) => a.DistanceRoundTrack - b.DistanceRoundTrack);

            // Initialize Plotly Graphs
            Plotly.newPlot(speedGraphDiv,
                [
                    {
                        x: telemetry.map(d => d.DistanceRoundTrack),
                        y: telemetry.map(d => d.SpeedMs),
                        mode: 'line',
                        type: 'line'
                    }
                ],
                {
                    title: 'Speed Data Over Distance',
                });

            Plotly.newPlot(throttleGraphDiv,
                [
                    {
                        x: telemetry.map(d => d.DistanceRoundTrack),
                        y: telemetry.map(d => d.Throttle),
                        mode: 'line',
                        type: 'line'
                    }
                ],
                {
                    title: 'Throttle Data Over Distance'
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
            Plotly.newPlot(mapDiv, [trace], layout);
            // set the min and max values of the distance slider
            distanceSlider.min = telemetry[0].DistanceRoundTrack;
            distanceSlider.max = telemetry[telemetry.length - 1].DistanceRoundTrack;

            updateLap();
            updateDistance();
        });

        function updateLap() {
            const selectedLap = parseInt(lapSelector.value);

            // Filter data for the selected lap
            const filteredTelemetry = telemetry.filter(item => item.CurrentLap === selectedLap);

            // Update Plotly Graphs
            Plotly.restyle(speedGraphDiv, 'x', [filteredTelemetry.map(d => d.DistanceRoundTrack)]);
            Plotly.restyle(speedGraphDiv, 'y', [filteredTelemetry.map(d => d.SpeedMs)]);
            Plotly.restyle(throttleGraphDiv, 'x', [filteredTelemetry.map(d => d.DistanceRoundTrack)]);
            Plotly.restyle(throttleGraphDiv, 'y', [filteredTelemetry.map(d => d.Throttle)]);
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
