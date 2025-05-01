# 🌐 Professional Transportation Planner

## Overview

The Professional Transportation Planner is an intelligent route analysis and navigation application that leverages AI to provide comprehensive transportation insights. This project combines geolocation services, route planning, and an AI-powered assistant to help users make informed travel decisions.

## 🚀 Key Features

- **Multi-Modal Route Planning**: Compare routes across different transportation modes
- **AI-Powered Insights**: Get intelligent recommendations and information about your route
- **Comprehensive Route Analysis**: 
  - Detailed route information
  - Cost estimation
  - Environmental impact assessment
  - Travel time calculations

## 🛠 Tech Stack

- **Backend**: Python
- **Web Framework**: Gradio
- **AI Integration**: RAG (Retrieval-Augmented Generation) System
- **Geolocation**: GraphHopper API
- **Dependencies**: See `requirements.txt`

## 📦 Prerequisites

- Python 3.8+
- GraphHopper API Key
- Virtual environment recommended

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/bahodir4/software-engineering-devasc.git
cd route-planner-rag
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root and add:
```
TRACE=your_graphhopper_api_key
# Add any other necessary environment variables
```

## 🚀 Running the Application

```bash
python main.py
```

The application will launch on `http://localhost:8000`

## 🤖 Usage

### Route Planner
1. Enter your origin location
2. Enter your destination
3. Click "Analyze Route"
4. View detailed route comparisons

### AI Route Insights
1. Plan a route first
2. Ask questions about your route
3. Optionally select a transport mode preference
4. Get AI-powered insights

## 📊 Transport Modes Supported

- 🚗 Car
- 🚲 Bicycle
- 🚶 Walking
- 🚌 Public Bus
- ✈️ Airplane

## 🔍 Environmental Impact Tracking

Each route provides an environmental impact assessment to help you make eco-friendly travel choices.

## 🛡 Error Handling

Robust error handling with descriptive messages for:
- Geocoding issues
- Route planning errors
- AI query limitations

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📋 Configuration

Modify `main.py` or use environment variables to customize:
- API endpoints
- Transport mode details
- AI query parameters

## 🔒 Security

- Requires API key for geolocation services
- Implements error handling to prevent information exposure

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Contact

Your Name - bakhodirnematanov@gmail.com
Project Link: [https://github.com/bahodir4/software-engineering-devasc.git]
## 🙏 Acknowledgements

- [Gradio](https://www.gradio.app/)
- [GraphHopper](https://www.graphhopper.com/)
- [Python](https://www.python.org/)

---

**Note**: This project is a demonstration of AI-powered route planning and should be used for informational purposes.