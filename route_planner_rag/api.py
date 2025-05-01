import os
import asyncio
import requests
import urllib.parse
import gradio as gr
import traceback
from typing import Optional, Dict, Any, AsyncGenerator

# Import the core components from the original script
from main import RAGSystem, geocoding, calculate_additional_transport_times

class ProfessionalTransportationPlanner:
    def __init__(self):
        # Global route storage
        self.global_route_data = {
            "origin": None,
            "destination": None,
            "routes": {}
        }
        
        # Comprehensive transport mode details
        self.transport_modes = {
            "car": {
                "name": "Car",
                "icon": "🚗",
                "avg_speed": 60,  # km/h
                "cost_per_km": 0.15,  # Estimated fuel and maintenance
                "environmental_impact": "High",
                "best_for": ["Flexibility", "Long distances", "Group travel"]
            },
            "bike": {
                "name": "Bicycle",
                "icon": "🚲",
                "avg_speed": 15,  # km/h
                "cost_per_km": 0.01,  # Minimal maintenance
                "environmental_impact": "Very Low",
                "best_for": ["Short distances", "Exercise", "Urban areas"]
            },
            "foot": {
                "name": "Walking",
                "icon": "🚶",
                "avg_speed": 5,  # km/h
                "cost_per_km": 0,
                "environmental_impact": "Zero",
                "best_for": ["Short distances", "Exploration", "Health"]
            },
            "bus": {
                "name": "Public Bus",
                "icon": "🚌",
                "avg_speed": 25,  # km/h
                "cost_per_km": 0.10,  # Public transit fare
                "environmental_impact": "Low",
                "best_for": ["Budget travel", "Urban commuting", "No parking hassles"]
            },
            "airplane": {
                "name": "Airplane",
                "icon": "✈️",
                "avg_speed": 800,  # km/h
                "cost_per_km": 0.50,  # Varies widely
                "environmental_impact": "High",
                "best_for": ["Long distances", "International travel", "Time-sensitive trips"]
            }
        }
        
        # Initialize RAG system
        self.rag_system = RAGSystem()
    
    def geocode_location(self, location: str) -> Dict[str, Any]:
        """Advanced geocoding with comprehensive details"""
        try:
            key = os.getenv("TRACE")  # GraphHopper API key
            status, lat, lng, formatted_loc = geocoding(location, key)
            
            if status != 200 or lat == "null" or lng == "null":
                return {
                    "status": "error",
                    "message": f"Could not geocode location: {location}",
                    "details": "Possible reasons: Incomplete address, typo, or unsupported location"
                }
            
            return {
                "status": "success",
                "location": formatted_loc,
                "latitude": lat,
                "longitude": lng,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Geocoding error: {str(e)}",
                "details": "Unable to process location. Please check the address and try again."
            }
    
    def plan_route(self, origin: str, destination: str) -> str:
        """Comprehensive route planning with detailed insights"""
        try:
            # Geocode locations
            orig_data = self.geocode_location(origin)
            dest_data = self.geocode_location(destination)
            
            if orig_data["status"] == "error" or dest_data["status"] == "error":
                return f"""
                <div class="route-error-card">
                    <h2>🚨 Route Planning Error</h2>
                    <p><strong>Origin:</strong> {orig_data.get('message', 'Unknown origin error')}</p>
                    <p><strong>Destination:</strong> {dest_data.get('message', 'Unknown destination error')}</p>
                    <p>Please verify your locations and try again.</p>
                </div>
                """
            
            # Reset global route data
            self.global_route_data = {
                "origin": orig_data["location"],
                "destination": dest_data["location"],
                "routes": {}
            }
            
            # Supported transport modes
            transport_modes = ["car", "bike", "foot", "bus", "airplane"]
            
            # HTML for route summary
            route_summary = f"""
            <div class="route-info-card">
                <h2>🗺️ Route Analysis</h2>
                <div class="route-details">
                    <p><strong>From:</strong> {orig_data['location']}</p>
                    <p><strong>To:</strong> {dest_data['location']}</p>
                </div>
            </div>
            
            <div class="route-comparison-card">
                <h3>🚦 Transport Mode Comparison</h3>
                <div class="route-table-container">
                    <table class="route-table">
                        <thead>
                            <tr>
                                <th>Mode</th>
                                <th>Duration</th>
                                <th>Distance</th>
                                <th>Cost Est.</th>
                                <th>Environmental Impact</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            # Route URL and key
            route_url = "https://graphhopper.com/api/1/route?"
            key = os.getenv("TRACE")
            
            # Process each transport mode
            for vehicle in transport_modes:
                # Construct URL for API-supported modes
                if vehicle in ["car", "bike", "foot"]:
                    op = f"&point={orig_data['latitude']}%2C{orig_data['longitude']}"
                    dp = f"&point={dest_data['latitude']}%2C{dest_data['longitude']}"
                    
                    paths_url = route_url + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + op + dp
                    paths_response = requests.get(paths_url)
                    
                    if paths_response.status_code == 200:
                        paths_data = paths_response.json()
                        
                        if "paths" in paths_data and len(paths_data["paths"]) > 0:
                            path = paths_data["paths"][0]
                            miles = path["distance"] / 1000 / 1.61
                            km = path["distance"] / 1000
                            sec = int(path["time"] / 1000 % 60)
                            min = int(path["time"] / 1000 / 60 % 60)
                            hr = int(path["time"] / 1000 / 60 / 60)
                            
                            # Estimated cost calculation
                            mode_details = self.transport_modes.get(vehicle, {})
                            est_cost = km * mode_details.get('cost_per_km', 0)
                            
                            route_summary += f"""
                            <tr>
                                <td>
                                    {mode_details.get('icon', '')} 
                                    {mode_details.get('name', vehicle.capitalize())}
                                </td>
                                <td>{hr:02d}:{min:02d}:{sec:02d}</td>
                                <td>{km:.1f} km</td>
                                <td>${est_cost:.2f}</td>
                                <td>{mode_details.get('environmental_impact', 'Unknown')}</td>
                            </tr>
                            """
                            
                            # Store route data
                            self.global_route_data["routes"][vehicle] = {
                                "duration": f"{hr:02d}:{min:02d}:{sec:02d}",
                                "distance_km": km,
                                "distance_miles": miles,
                                "estimated_cost": est_cost
                            }
                
                # Handle estimated modes (bus, airplane)
                else:
                    # Estimate based on car route
                    base_car_distance = 100  # Default km
                    duration_minutes = calculate_additional_transport_times(base_car_distance, vehicle)
                    
                    hr, min_remainder = divmod(duration_minutes, 60)
                    min, sec = divmod(min_remainder * 60, 60)
                    miles = base_car_distance / 1.61
                    
                    # Estimated cost calculation
                    mode_details = self.transport_modes.get(vehicle, {})
                    est_cost = base_car_distance * mode_details.get('cost_per_km', 0)
                    
                    route_summary += f"""
                    <tr>
                        <td>
                            {mode_details.get('icon', '')} 
                            {mode_details.get('name', vehicle.capitalize())} 
                            <small>(Estimated)</small>
                        </td>
                        <td>{int(hr):02d}:{int(min):02d}:{int(sec):02d}</td>
                        <td>{base_car_distance:.1f} km</td>
                        <td>${est_cost:.2f}</td>
                        <td>{mode_details.get('environmental_impact', 'Unknown')}</td>
                    </tr>
                    """
                    
                    # Store estimated route data
                    self.global_route_data["routes"][vehicle] = {
                        "duration": f"{int(hr):02d}:{int(min):02d}:{int(sec):02d}",
                        "distance_km": base_car_distance,
                        "distance_miles": miles,
                        "estimated_cost": est_cost,
                        "estimated": True
                    }
            
            route_summary += """
                        </tbody>
                    </table>
                </div>
            </div>
            """
            
            return route_summary
        
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Comprehensive route planning error: {error_trace}")
            return f"""
            <div class="route-error-card">
                <h2>🚨 Unexpected Error</h2>
                <p>An unexpected error occurred during route planning.</p>
                <p>Error Details: {str(e)}</p>
                <p>Please try again or contact support.</p>
            </div>
            """
    
    async def stream_route_query(self, query: str, transport_preference: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Streaming AI-powered route query with enhanced context"""
        try:
            # Check if routes have been planned
            if not self.global_route_data.get("origin") or not self.global_route_data.get("destination"):
                yield """
                <div class="route-warning-card">
                    <h2>⚠️ Query Limitation</h2>
                    <p>Please plan a route first before asking about it.</p>
                    <p>Use the 'Route Planning' tab to create a route, then ask questions.</p>
                </div>
                """
                return
            
            # Enhance query with route context
            context = f"Route from {self.global_route_data['origin']} to {self.global_route_data['destination']}"
            full_query = f"{query} ({context})"
            
            # Streaming response simulation (replace with actual streaming implementation)
            # Here we'll use the original query method but simulate streaming
            response = self.rag_system.query(full_query, transport_preference)
            
            # Start the response
            yield f"""
            <div class="ai-response-card">
                <h3>🤖 AI Route Assistant</h3>
                <div class="ai-response-content">
            """
            
            # Simulate streaming by yielding chunks of text
            words = response["answer"].split()
            current_chunk = ""
            for word in words:
                current_chunk += word + " "
                # Yield chunks to simulate streaming
                if len(current_chunk.split()) % 5 == 0:
                    yield f"{current_chunk}"
                await asyncio.sleep(0.1)  # Small delay to simulate streaming
            
            # Yield any remaining text
            if current_chunk:
                yield f"{current_chunk}"
            
            # Close the response div
            yield """
                </div>
                <div class="ai-response-tip">
                    <p>💡 Tip: This response is AI-generated based on available route information.</p>
                </div>
            </div>
            """
        
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Route query error: {error_trace}")
            yield f"""
            <div class="route-error-card">
                <h2>🚨 Query Error</h2>
                <p>Unable to process your query.</p>
                <p>Error Details: {str(e)}</p>
            </div>
            """

def create_gradio_interface():
    """Create a professional Gradio interface with enhanced styling"""
    # Comprehensive CSS for professional design
    css = """
    /* Global Styling */
    .gradio-container {
        font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
        background-color: #0f1429;
        color: #e0e0e0;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }

    /* Typography */
    h1, h2, h3 {
        color: #ffffff;
        font-weight: 600;
        margin-bottom: 15px;
    }

    /* Input Styling */
    .gradio-container .form .input-text {
        background-color: #1a2138;
        border: 1px solid #2c3e50;
        color: #ffffff;
        padding: 10px;
        border-radius: 6px;
        transition: all 0.3s ease;
    }

    .gradio-container .form .input-text:focus {
        border-color: #3498db;
        box-shadow: 0 0 10px rgba(52, 152, 219, 0.3);
    }

    /* Button Styling */
    .gradio-container .button {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .gradio-container .button:hover {
        background-color: #2980b9;
        transform: translateY(-2px);
    }

    /* Card Styling */
    .route-info-card, 
    .route-comparison-card, 
    .ai-response-card, 
    .route-error-card, 
    .route-warning-card {
        background-color: #1a2138;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .route-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }

    .route-table th {
        background-color: #2c3e50;
        color: #ecf0f1;
        padding: 12px;
        text-align: left;
        border-bottom: 2px solid #34495e;
    }

    .route-table td {
        padding: 12px;
        border-bottom: 1px solid #2c3e50;
        color: #bdc3c7;
    }

    .route-table tr:hover {
        background-color: #2c3e50;
        transition: background-color 0.3s ease;
    }

    /* AI Response Styling */
    .ai-response-content {
        background-color: #252b42;
        padding: 15px;
        border-radius: 8px;
        line-height: 1.6;
        color: #e0e0e0;
    }

    .ai-response-tip {
        margin-top: 15px;
        font-size: 0.9em;
        color: #7f8c8d;
        font-style: italic;
    }

    /* Error and Warning Cards */
    .route-error-card {
        border-left: 5px solid #e74c3c;
    }

    .route-warning-card {
        border-left: 5px solid #f39c12;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .gradio-container {
            padding: 10px;
        }

        .route-table {
            font-size: 0.9em;
        }

        .route-table th, .route-table td {
            padding: 8px;
        }
    }
    """
    
    # Initialize the planner
    planner = ProfessionalTransportationPlanner()
    
    # Create Gradio interface
    with gr.Blocks(css=css, title="Professional Transportation Planner", theme=gr.themes.Soft()) as demo:
        # Header with professional branding
        gr.Markdown("""
        # 🌐 Professional Transportation Planner
        ## Intelligent Route Analysis & AI-Powered Navigation
        """)
        
        # Main interface layout with enhanced tabs
        with gr.Tabs() as tabs:
            # Route Planner Tab
            with gr.Tab("Route Planner", id="route-planner"):
                # Input section with improved layout
                with gr.Row():
                    origin_input = gr.Textbox(
                        label="Origin Location", 
                        placeholder="Enter precise starting point (e.g., 123 Main St, New York, NY)",
                        info="🌍 Provide a detailed, specific location for best results",
                        scale=1
                    )
                    destination_input = gr.Textbox(
                        label="Destination Location", 
                        placeholder="Enter precise destination (e.g., 456 Elm St, Boston, MA)",
                        info="🏁 Enter a complete, accurate address",
                        scale=1
                    )
                
                # Advanced options row
                with gr.Row():
                    # Plan Route Button with enhanced styling
                    plan_route_btn = gr.Button(
                        "📍 Analyze Route", 
                        variant="primary"
                    )
                
                # Results section
                route_output = gr.HTML(label="🗺️ Detailed Route Analysis")
            
            # AI Insights Tab
            with gr.Tab("Route Insights", id="route-insights"):
                # Query input with context-aware placeholder
                query_input = gr.Textbox(
                    label="Ask AI Route Assistant", 
                    placeholder="What specific insights do you need about your planned route?",
                    info="💡 Ask questions about transportation, local info, or route details"
                )
                
                # Transport mode preference with icons
                transport_pref = gr.Dropdown(
                    ["car", "bike", "foot", "bus", "airplane"], 
                    label="📋 Preferred Transport Mode (Optional)",
                    info="Narrow down AI insights to a specific mode of transport"
                )
                
                # Insights Button with professional styling
                query_btn = gr.Button(
                    "🤖 Get AI Insights", 
                    variant="primary"
                )
                
                # Streaming AI Response Output
                query_output = gr.HTML(label="🧠 AI Route Insights")
        
        # Event Handlers with async support
        plan_route_btn.click(
            fn=planner.plan_route, 
            inputs=[origin_input, destination_input], 
            outputs=route_output
        )
        
        query_btn.click(
            fn=planner.stream_route_query,
            inputs=[query_input, transport_pref],
            outputs=query_output,
            api_name="route_insights"
        )
    
    return demo

def main():
    # Create and launch the interface with additional configurations
    demo = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=8000,
        share=True,
        debug=True  # Enable debug mode for development
    )

if __name__ == "__main__":
    main()