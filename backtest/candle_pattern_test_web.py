#!/usr/bin/env python3
import subprocess
import json
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route("/")
def index():
    # Run backtest and capture lines
    raw = subprocess.check_output(
        ["python3", "backtest/candle_pattern_test.py"],
        stderr=subprocess.DEVNULL
    ).decode().strip().splitlines()

    # Parse into list of dicts
    data = []
    for line in raw[1:]:
        parts = line.split(", ")
        if len(parts) < 8:
            continue
        try:
            ts = parts[0]
            o = float(parts[1].split("=")[1])
            h = float(parts[2].split("=")[1])
            l = float(parts[3].split("=")[1])
            c = float(parts[4].split("=")[1])
            try:
                s5 = float(parts[5].split("=")[1].split(" ")[0])
            except:
                s5 = 0.0
            try:
                e5 = float(parts[6].split("=")[1].split(" ")[0])
            except:
                e5 = 0.0
            try:
                f5 = float(parts[7].split("=")[1])
            except:
                f5 = 0.0

            data.append({
                "time": ts,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "S5": s5,
                "E5": e5,
                "F5": f5
            })
        except:
            continue

    plot_data = json.dumps(data)
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Candle Pattern Visualizer</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>body{{margin:0;}} #chart{{width:100vw;height:100vh;}}</style>
</head>
<body>
  <div id="chart"></div>
  <script>
    const data = {plot_data};

    // Build arrays
    const times  = data.map(d => d.time);
    const opens  = data.map(d => d.open);
    const highs  = data.map(d => d.high);
    const lows   = data.map(d => d.low);
    const closes = data.map(d => d.close);

    // Pack ALL values into customdata for hover
    const allvals = data.map(d => [
      d.open, d.high, d.low, d.close,
      d.S5, d.E5, d.F5
    ]);

    // Candlestick trace (no hover of its own)
    const candleTrace = {{
      x: times,
      open: opens,
      high: highs,
      low: lows,
      close: closes,
      increasing: {{line:{{color:'green'}},fillcolor:'rgba(0,128,0,0.3)'}},
      decreasing: {{line:{{color:'red'}},fillcolor:'rgba(255,0,0,0.3)'}},
      type: 'candlestick',
      hoverinfo: 'skip'
    }};

    // Invisible scatter purely for hover
    const hoverTrace = {{
      x: times,
      y: closes,     // place markers at the closing price
      customdata: allvals,
      mode: 'markers',
      marker: {{opacity:0, size:20}},
      hovertemplate:
        'Time: %{{x}}<br>' +
        'O: %{{customdata[0]}}<br>' +
        'H: %{{customdata[1]}}<br>' +
        'L: %{{customdata[2]}}<br>' +
        'C: %{{customdata[3]}}<br>' +
        'S5: %{{customdata[4]}}<br>' +
        'E5: %{{customdata[5]}}<br>' +
        'F5: %{{customdata[6]}}<br>' +
        '<extra></extra>'
    }};

    // Buy/sell highlight shapes
    const shapes = [];
    const pad = 0.0001 * (Math.max(...highs) - Math.min(...lows));
    data.forEach((d,i) => {{
      const next = data[i+1]?data[i+1].time:d.time;
      if (d.S5>0||d.E5>0||d.F5>0) {{
        shapes.push({{type:'rect',x0:d.time,x1:next,
          y0:Math.min(...lows)-pad,y1:Math.max(...highs)+pad,
          fillcolor:'rgba(0,255,0,0.1)',line:{{width:0}}}});
      }} else if (d.S5<0||d.E5<0||d.F5<0) {{
        shapes.push({{type:'rect',x0:d.time,x1:next,
          y0:Math.min(...lows)-pad,y1:Math.max(...highs)+pad,
          fillcolor:'rgba(255,0,0,0.1)',line:{{width:0}}}});
      }}
    }});

    const layout = {{
      xaxis: {{title:'Time',type:'date',rangeslider:{{visible:false}}}},
      yaxis: {{title:'Price'}},
      shapes: shapes,
      margin:{{t:20,b:40,l:50,r:20}},
      dragmode:'zoom'
    }};

    Plotly.newPlot('chart',[candleTrace,hoverTrace],layout,{{responsive:true}});
  </script>
</body>
</html>
"""
    return render_template_string(html)

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8080,debug=True)

