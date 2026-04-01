# bc-shuttle-tracker

Human-AI collaborative shuttle tracking system for Boston College.

## Features

- 🗺️ Live GPS tracking with interactive map
- 🛣️ Multi-route live map with moving shuttle simulation
- 🎯 Transparent AI confidence levels (87%, 62%, etc.)
- 👥 Real-time capacity information
- ✓ User verification and feedback
- 🚗 Driver quick-tap interface
- 🎛️ Dispatcher override controls

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## How The Live Map Works

1. Route loops are defined as ordered latitude/longitude points in `shuttle_simulation.py`.
2. Each shuttle stores a route, speed, and progress along that loop.
3. `streamlit-autorefresh` reruns the app every 2 seconds.
4. On each rerun, shuttle progress advances, bus markers move, and ETAs are recalculated for the selected stop.
5. Driver and dispatcher pages update the same shared session-state fleet so rider-facing alerts stay synchronized.

## Deployment

Deployed at: https://bc-shuttle-tracker-8puopl5u2ctbgxwqrqx6nt.streamlit.app/
## Team

- Xiaoyin Liu
- Zimeng Yang
- Jaewon Park

## Course

CSCI 3360 - Human-AI Interaction  
Boston College, Spring 2026
