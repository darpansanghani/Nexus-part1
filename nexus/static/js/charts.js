/**
 * Google Charts Integration for NEXUS
 */

class ChartsManager {
    constructor() {
        this.isLoaded = false;
        
        // Load Google Charts
        if (window.google && window.google.charts) {
            google.charts.load('current', {'packages':['corechart', 'gauge']});
            google.charts.setOnLoadCallback(() => {
                this.isLoaded = true;
            });
        }
    }

    drawCharts(plan) {
        if (!this.isLoaded || !window.google || !google.visualization) return;

        this.drawConfidenceGauge(plan.confidence);
        this.drawPriorityBarChart(plan.immediate_actions);
    }

    drawConfidenceGauge(confidenceFloat) {
        const value = Math.round(confidenceFloat * 100);
        const data = google.visualization.arrayToDataTable([
            ['Label', 'Value'],
            ['Confidence', value]
        ]);

        const options = {
            width: '100%', height: 200,
            redFrom: 0, redTo: 60,
            yellowFrom:60, yellowTo: 85,
            greenFrom: 85, greenTo: 100,
            minorTicks: 5
        };

        const chartElement = document.getElementById('confidence-gauge');
        chartElement.setAttribute('aria-label', `Confidence score graph: ${value}%`);
        const chart = new google.visualization.Gauge(chartElement);
        chart.draw(data, options);
    }

    drawPriorityBarChart(actions) {
        if (!actions || actions.length === 0) return;

        // Group actions by severity/priority bins
        let highCount = 0, medCount = 0, lowCount = 0;
        
        actions.forEach(a => {
            if (a.priority <= 3) highCount++;
            else if (a.priority <= 6) medCount++;
            else lowCount++;
        });

        const data = google.visualization.arrayToDataTable([
            ['Priority Level', 'Actions', { role: 'style' }],
            ['Critical (1-3)', highCount, '#ff3b5e'],
            ['Moderate (4-6)', medCount, '#ff9f43'],
            ['Standard (7-10)', lowCount, '#2ecc71']
        ]);

        // Colors need to dynamically switch for dark theme, but we use hardcoded text colors for simplicity
        const textColor = document.documentElement.style.getPropertyValue('--color-text') || '#e8eaf0';

        const options = {
            title: 'Action Distribution',
            titleTextStyle: { color: textColor },
            backgroundColor: 'transparent',
            legend: { position: 'none' },
            hAxis: { 
                textStyle: { color: textColor },
                gridlines: { color: 'transparent' }
            },
            vAxis: { 
                textStyle: { color: textColor }
            },
            animation:{
                startup: true,
                duration: 1000,
                easing: 'out',
            }
        };

        const chartElement = document.getElementById('priority-bar-chart');
        chartElement.setAttribute('aria-label', 'Action distribution graph');
        const chart = new google.visualization.BarChart(chartElement);
        chart.draw(data, options);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.chartsManager = new ChartsManager();
});
