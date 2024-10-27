const priceChart = new Chart(document.getElementById('priceChart').getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Price',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                borderWidth: 2,
                pointRadius: 1,
                fill: false,
                order: 1
            },
            {
                label: 'SMA20',
                data: [],
                borderColor: 'rgba(255, 99, 132, 0.7)',
                backgroundColor: 'rgba(255, 99, 132, 0.7)',
                tension: 0.1,
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                order: 2
            },
            {
                label: 'SMA50',
                data: [],
                borderColor: 'rgba(54, 162, 235, 0.7)',
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                tension: 0.1,
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                order: 3
            },
            {
                label: 'Buy Signals',
                data: [],
                backgroundColor: 'rgba(75, 192, 75, 1)',
                pointStyle: 'triangle',
                pointRadius: 15,
                showLine: false,
                order: 0
            },
            {
                label: 'Sell Signals',
                data: [],
                backgroundColor: 'rgba(255, 99, 132, 1)',
                pointStyle: 'triangle',
                pointRadius: 15,
                rotation: 180,
                showLine: false,
                order: 0
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        scales: {
            y: {
                beginAtZero: false,
                grace: '5%',
                ticks: {
                    callback: function(value) {
                        return '$' + value.toLocaleString();
                    }
                }
            },
            x: {
                ticks: {
                    maxTicksLimit: 10,
                    maxRotation: 45,
                    minRotation: 45
                }
            }
        },
        plugins: {
            legend: {
                display: true,
                position: 'top'
            },
            tooltip: {
                enabled: true,
                callbacks: {
                    label: function(context) {
                        return context.dataset.label + ': $' + context.raw.toLocaleString();
                    }
                }
            }
        }
    }
});

function updateTradesTable(trades) {
    const tbody = document.querySelector('#trades-table tbody');
    tbody.innerHTML = '';
    
    console.log("Updating trades table with:", trades); // Debug log
    
    if (!trades || trades.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="5">No trades yet</td>';
        tbody.appendChild(row);
        return;
    }
    
    trades.forEach(trade => {
        const row = document.createElement('tr');
        const time = new Date(trade.timestamp).toLocaleString();
        const value = (trade.price * trade.amount).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        
        row.innerHTML = `
            <td>${time}</td>
            <td>${trade.type.toUpperCase()}</td>
            <td>$${trade.price.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            })}</td>
            <td>${trade.amount.toFixed(6)}</td>
            <td>$${value}</td>
        `;
        tbody.appendChild(row);
    });
}

async function updateData() {
    try {
        const response = await fetch('/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `ticker=${document.getElementById('ticker').value}`
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }

        // Update strategy description
        document.getElementById('strategy-text').textContent = data.strategy_description;

        // Update chart data
        priceChart.data.labels = data.timestamps;
        priceChart.data.datasets[0].data = data.historical_prices;
        priceChart.data.datasets[1].data = data.sma20_values;
        priceChart.data.datasets[2].data = data.sma50_values;

        // Update buy/sell signals
        priceChart.data.datasets[3].data = data.buy_signals.map(signal => ({
            x: signal.timestamp,
            y: signal.price
        }));
        priceChart.data.datasets[4].data = data.sell_signals.map(signal => ({
            x: signal.timestamp,
            y: signal.price
        }));

        priceChart.update();

        // Update other UI elements
        document.getElementById('portfolio-value').textContent = 
            `Current Portfolio Value: $${data.portfolio_value.toLocaleString()}`;
        document.getElementById('latest-price').textContent = 
            `Latest Price: $${data.price.toLocaleString()}`;
        document.getElementById('holdings').textContent = 
            `Current Holdings: ${data.holdings}`;
        document.getElementById('cash-balance').textContent = 
            `Cash Balance: $${data.cash.toLocaleString()}`;
        
        // Log the data before updating chart
        console.log("Updating chart with:");
        console.log("Timestamps:", data.timestamps.length);
        console.log("Prices:", data.historical_prices.length);
        console.log("First price:", data.historical_prices[0]);
        console.log("Last price:", data.historical_prices[data.historical_prices.length - 1]);
        
        // Update trades table
        updateTradesTable(data.trades);
        
    } catch (error) {
        console.error("Error updating data:", error);
    }
}

// Initial update
updateData();

// Auto-update every 5 minutes
setInterval(updateData, 300000);

async function runBacktest() {
    try {
        const ticker = document.getElementById('ticker').value;
        const days = document.getElementById('backtest-days').value;
        
        const response = await fetch('/backtest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `ticker=${ticker}&days=${days}`
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Display backtest results
        const resultsDiv = document.getElementById('backtest-results');
        resultsDiv.innerHTML = `
            <h4>Backtest Results</h4>
            <p>Initial Investment: $${data.initial_value.toLocaleString()}</p>
            <p>Final Value: $${data.final_value.toLocaleString()}</p>
            <p>Return: ${data.return_percentage}%</p>
            <p>Number of Trades: ${data.number_of_trades}</p>
            <h4>Trade History</h4>
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Type</th>
                        <th>Price</th>
                        <th>Amount</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.trades.map(trade => `
                        <tr>
                            <td>${new Date(trade.timestamp).toLocaleString()}</td>
                            <td>${trade.type.toUpperCase()}</td>
                            <td>$${trade.price.toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            })}</td>
                            <td>${trade.amount.toFixed(6)}</td>
                            <td>$${trade.value.toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            })}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        console.error("Backtest error:", error);
        alert("Error running backtest");
    }
}
