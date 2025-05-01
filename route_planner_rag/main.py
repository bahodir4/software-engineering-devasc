import requests
import urllib.parse
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
from typing import Dict, Any, List
from dotenv import load_dotenv
import datetime

load_dotenv()

# Set your API key here
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini model
gemini = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.2,
    max_output_tokens=1024
)

# Initialize Gemini embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001"  # Gemini's embedding model
)

# Create memory for conversation history
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

class RAGSystem:
    def __init__(self):
        self.vector_store = None
        self.retriever = None
        self.qa_chain = None
        self.initialize_vector_store()
        
    def initialize_vector_store(self):
        try:
            self.vector_store = Chroma(
                collection_name="graphhopper_routes",
                embedding_function=embeddings,
                persist_directory="./vector_db"
            )
            print("Vector store loaded successfully")
        except Exception as e:
            print(f"Creating new vector store: {e}")
            self.vector_store = Chroma(
                collection_name="graphhopper_routes",
                embedding_function=embeddings,
                persist_directory="./vector_db"
            )
            
        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 10}
        )
            
        # Setup updated QA chain with LCEL (LangChain Expression Language)
        self.template = """
        You are a helpful transportation assistant using route data.
        Based on the given context information about routes, directions, and locations,
        provide a helpful and natural response to the user's query.
        
        Chat History: {chat_history}
        
        Retrieved route information: 
        {context}
        
        User Query: {question}
        
        User's Transportation Preference: {transport_preference}
        
        Please provide a detailed response that includes:
        1. Clear directions in a conversational tone focused on the user's preferred mode of transport
        2. Relevant information about points of interest along the route
        3. Any necessary warnings, tips, or special considerations for the transportation mode
        4. Time and distance comparisons between different transport options if relevant
        5. Schedule information for public transportation if available
        6. Cost estimates if available
        
        Response:
        """
        
        self.prompt = PromptTemplate.from_template(self.template)
        
        # LCEL chain is set up in query method to avoid issues
    
    def format_docs(self, docs):
        """Format documents into a single string"""
        return "\n\n".join(doc.page_content for doc in docs)
    
    def store_route_data(self, paths_data, orig_loc, dest_loc, vehicle):
        """Store route data in vector database for RAG"""
        if "paths" not in paths_data or len(paths_data["paths"]) == 0:
            print("No valid path data to store")
            return
            
        documents = []
        path = paths_data["paths"][0]
        
        # Create a unique ID for this route
        route_id = f"{orig_loc}_to_{dest_loc}_{vehicle}"
        
        # Store route metadata
        miles = (path["distance"]) / 1000 / 1.61
        km = (path["distance"]) / 1000
        sec = int(path["time"] / 1000 % 60)
        min = int(path["time"] / 1000 / 60 % 60)
        hr = int(path["time"] / 1000 / 60 / 60)
        
        route_meta = f"""
        Route Information:
        Origin: {orig_loc}
        Destination: {dest_loc}
        Transportation Mode: {vehicle}
        Distance: {km:.1f} km ({miles:.1f} miles)
        Duration: {hr:02d}:{min:02d}:{sec:02d}
        Timestamp: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        
        documents.append(Document(page_content=route_meta, metadata={
            "type": "route_metadata",
            "origin": orig_loc,
            "destination": dest_loc,
            "mode": vehicle,
            "route_id": route_id
        }))
        
        # Store directions
        if "instructions" in path:
            for idx, instruction in enumerate(path["instructions"]):
                text = instruction["text"]
                distance = instruction["distance"]
                
                direction = f"""
                Step {idx+1}: {text}
                Distance: {distance/1000:.1f} km ({distance/1000/1.61:.1f} miles)
                Transportation Mode: {vehicle}
                """
                
                documents.append(Document(page_content=direction, metadata={
                    "type": "direction",
                    "step_number": idx+1,
                    "route_id": route_id,
                    "mode": vehicle
                }))
        
        # Store overall route summary
        summary = f"""
        Complete route from {orig_loc} to {dest_loc} by {vehicle}:
        - Total distance: {km:.1f} km ({miles:.1f} miles)
        - Estimated travel time: {hr:02d}:{min:02d}:{sec:02d}
        - Number of steps: {len(path.get('instructions', []))}
        """
        
        documents.append(Document(page_content=summary, metadata={
            "type": "route_summary",
            "route_id": route_id,
            "mode": vehicle
        }))
        
        # Add documents to vector store
        self.vector_store.add_documents(documents)
        print(f"Added {len(documents)} documents to vector store for {vehicle} mode")
    
    def store_additional_transport_info(self, orig_loc, dest_loc, vehicle, distance, duration):
        """Store estimated data for modes not directly supported by GraphHopper"""
        documents = []
        
        # Create a unique ID for this route
        route_id = f"{orig_loc}_to_{dest_loc}_{vehicle}"
        
        # Store route metadata with estimated information
        miles = distance / 1.61
        km = distance
        hr, min_remainder = divmod(duration, 60)
        min, sec = divmod(min_remainder, 1)
        sec *= 60
        
        route_meta = f"""
        Route Information (Estimated):
        Origin: {orig_loc}
        Destination: {dest_loc}
        Transportation Mode: {vehicle}
        Distance: {km:.1f} km ({miles:.1f} miles)
        Duration: {int(hr):02d}:{int(min):02d}:{int(sec):02d}
        Note: This is an estimated route as {vehicle} is not directly supported by the routing API.
        Timestamp: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        
        documents.append(Document(page_content=route_meta, metadata={
            "type": "route_metadata",
            "origin": orig_loc,
            "destination": dest_loc,
            "mode": vehicle,
            "route_id": route_id,
            "estimated": True
        }))
        
        # Store additional mode-specific information
        if vehicle == "bus":
            bus_info = f"""
            Bus Travel Information from {orig_loc} to {dest_loc}:
            - Estimated distance: {km:.1f} km ({miles:.1f} miles)
            - Estimated travel time: {int(hr):02d}:{int(min):02d}:{int(sec):02d}
            - Bus routes may vary by city and time of day
            - Consider checking local bus schedules for precise timing
            - Typical bus fare might range from $2-$5 depending on the city
            - Buses generally make more stops than direct car routes
            """
            documents.append(Document(page_content=bus_info, metadata={
                "type": "transport_info",
                "mode": "bus",
                "route_id": route_id
            }))
            
        elif vehicle == "airplane":
            plane_info = f"""
            Air Travel Information from {orig_loc} to {dest_loc}:
            - Flight distance: {km:.1f} km ({miles:.1f} miles)
            - Estimated flight time: {int(hr):02d}:{int(min):02d}:{int(sec):02d}
            - Add approximately 2-3 hours for airport security and boarding procedures
            - Ticket prices typically range from $150-$500 depending on advance booking
            - Consider booking flights in advance for better rates
            - Check with airlines for baggage restrictions and fees
            """
            documents.append(Document(page_content=plane_info, metadata={
                "type": "transport_info",
                "mode": "airplane",
                "route_id": route_id
            }))
        
        # Add documents to vector store
        self.vector_store.add_documents(documents)
        print(f"Added {len(documents)} estimated documents to vector store for {vehicle} mode")
    
    def query(self, user_query, transport_preference=None, user_location=None):
        """Answer questions about routes with focus on preferred transport mode"""
        # Enhance query with user location if available
        query_context = []
        if user_location:
            query_context.append(f"User is currently at {user_location}")
            
        if transport_preference:
            query_context.append(f"User prefers {transport_preference} transportation")
            
        if query_context:
            enhanced_query = f"{user_query} ({'; '.join(query_context)})"
        else:
            enhanced_query = user_query
            
        try:
            # Build the chain fresh each time to avoid reference issues
            # Get documents from retriever
            docs = self.retriever.get_relevant_documents(enhanced_query)
            context = self.format_docs(docs)
            
            # Get chat history
            chat_history = memory.load_memory_variables({})["chat_history"]
            
            # Create inputs dict
            inputs = {
                "context": context,
                "question": enhanced_query,
                "chat_history": chat_history,
                "transport_preference": transport_preference if transport_preference else "any"
            }
            
            # Format prompt
            formatted_prompt = self.prompt.format(**inputs)
            
            # Call the model directly
            model_response = gemini.invoke(formatted_prompt)
            
            # Convert to string
            result = str(model_response.content)
            
            return {
                "answer": result,
                "sources": []
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error querying RAG system: {e}")
            return {
                "answer": "I'm sorry, I couldn't process your request at this time.",
                "sources": []
            }

# Initialize RAG system
rag_system = RAGSystem()

# Original GraphHopper functions
def geocoding(location, key):
    while location == "":
        location = input("Enter the location again: ")
    
    geocode_url = "https://graphhopper.com/api/1/geocode?"
    url = geocode_url + urllib.parse.urlencode({"q": location, "limit": "1", "key": key})
    replydata = requests.get(url)
    json_data = replydata.json()
    json_status = replydata.status_code
    
    print("Geocoding API URL for " + location + ":\n" + url)
    
    if json_status == 200 and len(json_data["hits"]) != 0:
        lat = json_data["hits"][0]["point"]["lat"]
        lng = json_data["hits"][0]["point"]["lng"]
        name = json_data["hits"][0]["name"]
        value = json_data["hits"][0]["osm_value"]
        
        if "country" in json_data["hits"][0]:
            country = json_data["hits"][0]["country"]
        else:
            country = ""
            
        if "state" in json_data["hits"][0]:
            state = json_data["hits"][0]["state"]
        else:
            state = ""
            
        if len(state) != 0 and len(country) != 0:
            new_loc = name + ", " + state + ", " + country
        elif len(state) != 0:
            new_loc = name + ", " + country
        else:
            new_loc = name
            
        print("Geocoding API URL for " + new_loc + " (Location Type: " + value + ")\n" + url)
    else:
        lat = "null"
        lng = "null"
        new_loc = location
        
        if json_status != 200:
            print("Geocode API status: " + str(json_status) + "\nError message: " + json_data["message"])
            
    return json_status, lat, lng, new_loc

def calculate_additional_transport_times(distance_km, mode):
    """Calculate estimated times for transport modes not supported by GraphHopper"""
    if mode == "bus":
        # Bus is typically slower than car due to stops and traffic
        # Average speed ~20-30 km/h in urban areas
        avg_speed_kmh = 25
        duration_minutes = (distance_km / avg_speed_kmh) * 60
        return duration_minutes
    
    elif mode == "airplane":
        # Flight calculations are more complex
        # 1. Base flight time (cruising at ~800 km/h)
        # 2. Add taxi, takeoff, landing time (about 30 min)
        # Note: Very short flights aren't realistic, so min 30 min flight time
        
        if distance_km < 100:
            # Too short for flight, use placeholder
            return 30  # minimum flight time in minutes
            
        # Average cruising speed ~800 km/h, but effective speed lower due to takeoff/landing
        avg_speed_kmh = 700
        flight_time_minutes = (distance_km / avg_speed_kmh) * 60
        
        # Add taxi, takeoff, landing time
        total_time_minutes = flight_time_minutes + 30
        
        return max(30, total_time_minutes)  # Minimum 30 minutes
    
    return 0  # Default fallback

# Main function with enhanced multi-mode routing
def main():
    route_url = "https://graphhopper.com/api/1/route?"
    key = os.getenv("TRACE")  # GraphHopper API key
    
    # Define supported profiles
    api_supported_profiles = ["car", "bike", "foot"]
    additional_profiles = ["bus", "airplane"]
    all_profiles = api_supported_profiles + additional_profiles
    
    while True:
        print("\n============================================")
        print("🌍 MULTI-MODE TRANSPORTATION PLANNER 🌍")
        print("============================================")
        print("Available transportation modes:")
        print("Direct routing: car, bike, foot")
        print("Estimated routing: bus, airplane")
        print("============================================")
        
        choice = input("What would you like to do?\n1. Plan a new route\n2. Query about existing routes\n3. Quit\nEnter choice (1-3): ")
        
        if choice == "3" or choice.lower() in ["quit", "q", "exit"]:
            print("Thank you for using the Transportation Planner. Goodbye!")
            break
            
        elif choice == "2" or choice.lower() in ["query", "ask"]:
            # Query mode - ask questions about stored routes
            user_query = input("What would you like to know about your routes? ")
            if user_query.lower() in ["quit", "q", "exit"]:
                break
                
            # Get current location if available
            current_loc = input("Your current location (optional, press Enter to skip): ")
            if current_loc.lower() in ["quit", "q", "exit"]:
                break
                
            # Get transport preference if any
            transport_pref = input("Do you have a preferred mode of transport? (car/bike/foot/bus/airplane or press Enter for any): ")
            if transport_pref.lower() in ["quit", "q", "exit"]:
                break
                
            if transport_pref.lower() not in all_profiles:
                transport_pref = None
                
            # Query the RAG system
            response = rag_system.query(
                user_query, 
                transport_pref if transport_pref else None, 
                current_loc if current_loc else None
            )
            
            print("\n=================================================")
            print("🤖 AI ASSISTANT RESPONSE:")
            print("=================================================")
            print(response["answer"])
            print("=================================================")
            continue
            
        elif choice == "1":
            # Route planning mode
            loc1 = input("Starting Location: ")
            if loc1.lower() in ["quit", "q", "exit"]:
                break
            
            orig = geocoding(loc1, key)
            
            loc2 = input("Destination: ")
            if loc2.lower() in ["quit", "q", "exit"]:
                break
            
            dest = geocoding(loc2, key)
            
            if orig[0] != 200 or dest[0] != 200:
                print("Error with geocoding one or both locations. Please try again.")
                continue
                
            print("\nFetching routes for all transportation modes...")
            print("=================================================")
            
            # Store the resulting paths data for each mode
            all_paths_data = {}
            base_car_distance = None
            
            # First get routes for API-supported modes
            for vehicle in api_supported_profiles:
                op = "&point=" + str(orig[1]) + "%2C" + str(orig[2])
                dp = "&point=" + str(dest[1]) + "%2C" + str(dest[2])
                
                paths_url = route_url + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + op + dp
                paths_response = requests.get(paths_url)
                paths_status = paths_response.status_code
                
                if paths_status == 200:
                    paths_data = paths_response.json()
                    all_paths_data[vehicle] = paths_data
                    
                    # Store car distance for estimating other modes
                    if vehicle == "car" and "paths" in paths_data and len(paths_data["paths"]) > 0:
                        base_car_distance = paths_data["paths"][0]["distance"] / 1000  # km
                    
                    # Store in RAG system
                    rag_system.store_route_data(paths_data, orig[3], dest[3], vehicle)
                else:
                    print(f"Error fetching {vehicle} route: {paths_response.json().get('message', 'Unknown error')}")
            
            # Now estimate for additional modes if we have car data
            if base_car_distance:
                for vehicle in additional_profiles:
                    # Calculate estimated times based on the car distance
                    duration_minutes = calculate_additional_transport_times(base_car_distance, vehicle)
                    
                    # Store in RAG system with estimated data
                    rag_system.store_additional_transport_info(
                        orig[3], dest[3], vehicle, 
                        base_car_distance,  # Use car distance as estimate
                        duration_minutes
                    )
            
            # Display summary of all routes
            print("\n=================================================")
            print(f"ROUTE SUMMARY: {orig[3]} to {dest[3]}")
            print("=================================================")
            
            for vehicle in api_supported_profiles:
                if vehicle in all_paths_data and "paths" in all_paths_data[vehicle] and len(all_paths_data[vehicle]["paths"]) > 0:
                    path_data = all_paths_data[vehicle]["paths"][0]
                    miles = path_data["distance"] / 1000 / 1.61
                    km = path_data["distance"] / 1000
                    sec = int(path_data["time"] / 1000 % 60)
                    min = int(path_data["time"] / 1000 / 60 % 60)
                    hr = int(path_data["time"] / 1000 / 60 / 60)
                    
                    print(f"🔹 {vehicle.upper()}: {hr:02d}:{min:02d}:{sec:02d} - {km:.1f} km ({miles:.1f} miles)")
            
            # Show estimated times for additional modes
            if base_car_distance:
                for vehicle in additional_profiles:
                    duration_minutes = calculate_additional_transport_times(base_car_distance, vehicle)
                    hr, min_remainder = divmod(duration_minutes, 60)
                    min, sec = divmod(min_remainder * 60, 60)
                    miles = base_car_distance / 1.61
                    
                    print(f"🔸 {vehicle.upper()} (estimated): {int(hr):02d}:{int(min):02d}:{int(sec):02d} - {base_car_distance:.1f} km ({miles:.1f} miles)")
            
            print("=================================================")
            
            # Ask for detailed route information of preferred mode
            pref_mode = input("\nWhich mode of transport would you like detailed directions for? ")
            if pref_mode.lower() in ["quit", "q", "exit"]:
                break
                
            # Default to car if input is not valid
            if pref_mode.lower() not in all_profiles:
                print(f"'{pref_mode}' is not a valid mode. Showing car directions by default.")
                pref_mode = "car"
            
            # Display detailed directions for API-supported modes
            if pref_mode in api_supported_profiles and pref_mode in all_paths_data:
                paths_data = all_paths_data[pref_mode]
                
                print("\n=================================================")
                print(f"DETAILED {pref_mode.upper()} DIRECTIONS:")
                print("=================================================")
                
                if "paths" in paths_data and len(paths_data["paths"]) > 0 and "instructions" in paths_data["paths"][0]:
                    for each in range(len(paths_data["paths"][0]["instructions"])):
                        path = paths_data["paths"][0]["instructions"][each]["text"]
                        distance = paths_data["paths"][0]["instructions"][each]["distance"]
                        print(f"{each+1}. {path} ({distance/1000:.1f} km / {distance/1000/1.61:.1f} miles)")
                else:
                    print("No detailed directions available.")
            else:
                print(f"\n{pref_mode.upper()} directions are estimated and don't have turn-by-turn navigation.")
                print("Consider using the AI assistant to get more information.")
            
            # Ask if user wants AI-enhanced information
            enhance = input("\nWould you like AI-enhanced information about this route? (y/n): ")
            if enhance.lower() == "y":
                # Create a proper query for the AI assistant
                query = f"Tell me about the route from {orig[3]} to {dest[3]} with a focus on {pref_mode} transportation"
                response = rag_system.query(query, pref_mode)
                
                print("\n=================================================")
                print("🤖 AI-ENHANCED ROUTE INFORMATION:")
                print("=================================================")
                print(response["answer"])
                print("=================================================")
                
            print("\n*************************************************")
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()