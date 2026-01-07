# 3D Ball Visualization Web App

A simple web application to visualize a 3D ball in an interactive environment with rotation and zoom capabilities.

## Features

- Interactive 3D visualization using Three.js
- Rotate: Left click + drag
- Pan: Right click + drag
- Zoom: Mouse scroll/wheel
- Real-time statistics display
- 904,089 voxel rendering

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the App

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## Project Structure

```
HCMQC_BS/
├── app.py                      # Flask web server
├── templates/
│   └── index.html             # Main visualization page
├── static/
│   └── ball_data.json         # 3D ball voxel data
├── generate_ball.py           # Script to generate ball array
├── convert_to_json.py         # Script to convert numpy to JSON
├── playground.py              # Testing script
└── requirements.txt           # Python dependencies
```

## API Endpoints

- `GET /` - Main visualization page
- `GET /health` - Health check endpoint
- `GET /static/ball_data.json` - Ball data JSON

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, JavaScript
- **3D Rendering**: Three.js
- **Data Format**: JSON
