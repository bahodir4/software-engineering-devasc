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
        template = """
        You are a helpful route planning assistant using GraphHopper data.
        Based on the given context information about routes, directions, and locations,
        provide a helpful and natural response to the user's query.
        
        Chat History: {chat_history}
        
        Retrieved route information: 
        {context}
        
        User Query: {question}
        
        Please provide a detailed response that includes:
        1. Clear directions in a conversational tone
        2. Relevant information about points of interest
        3. Any necessary warnings or tips for the route
        
        Response:
        """
        
        prompt = PromptTemplate.from_template(template)
        
        # Set up the LCEL chain
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
            
        # This creates a chain using the newer LCEL approach
        self.qa_chain = (
            {"context": self.retriever | format_docs, 
             "question": RunnablePassthrough(), 
             "chat_history": lambda _: memory.load_memory_variables({})["chat_history"]}
            | prompt 
            | gemini 
            | StrOutputParser()
        )
    
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
                """
                
                documents.append(Document(page_content=direction, metadata={
                    "type": "direction",
                    "step_number": idx+1,
                    "route_id": route_id
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
            "route_id": route_id
        }))
        
        # Add documents to vector store
        self.vector_store.add_documents(documents)
        print(f"Added {len(documents)} documents to vector store")
        
        # No need to explicitly persist - Chroma does this automatically now
    
    def query(self, user_query, user_location=None):
        """Answer questions about routes"""
        # Enhance query with user location if available
        if user_location:
            enhanced_query = f"{user_query} (User is currently at {user_location})"
        else:
            enhanced_query = user_query
            
        try:
            # Use the invoke method instead of __call__
            result = self.qa_chain.invoke(enhanced_query)
            
            return {
                "answer": result,
                "sources": []  # Sources aren't automatically returned in the new LCEL pattern
            }
        except Exception as e:
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

# Main function with RAG integration
def main():
    route_url = "https://graphhopper.com/api/1/route?"
    key = os.getenv("TRACE")  # GraphHopper API key
    
    while True:
        print("\n+++++++++++++++++++++++++++++++++++++++++++++")
        print("Vehicle profiles available on Graphhopper:")
        print("+++++++++++++++++++++++++++++++++++++++++++++")
        print("car, bike, foot")
        print("+++++++++++++++++++++++++++++++++++++++++++++")
        
        profile = ["car", "bike", "foot"]
        vehicle = input("Enter a vehicle profile from the list above (or 'query' to ask about routes, 'q' to quit): ")
        
        if vehicle == "quit" or vehicle == "q":
            break
        elif vehicle == "query":
            # Query mode - ask questions about stored routes
            user_query = input("What would you like to know about your routes? ")
            if user_query == "quit" or user_query == "q":
                break
                
            # Get current location if available
            current_loc = input("Your current location (optional, press Enter to skip): ")
            if current_loc == "quit" or current_loc == "q":
                break
                
            # Query the RAG system
            response = rag_system.query(user_query, current_loc if current_loc else None)
            
            print("\n=================================================")
            print("AI Response:")
            print("=================================================")
            print(response["answer"])
            print("=================================================")
            continue
        elif vehicle in profile:
            vehicle = vehicle
        else:
            vehicle = "car"
            print("No valid vehicle profile was entered. Using the car profile.")
        
        # Normal route planning mode
        loc1 = input("Starting Location: ")
        if loc1 == "quit" or loc1 == "q":
            break
        
        orig = geocoding(loc1, key)
        
        loc2 = input("Destination: ")
        if loc2 == "quit" or loc2 == "q":
            break
        
        dest = geocoding(loc2, key)
        
        print("=================================================")
        
        if orig[0] == 200 and dest[0] == 200:
            op = "&point=" + str(orig[1]) + "%2C" + str(orig[2])
            dp = "&point=" + str(dest[1]) + "%2C" + str(dest[2])
            
            paths_url = route_url + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + op + dp
            paths_status = requests.get(paths_url).status_code
            paths_data = requests.get(paths_url).json()
            
            print("Routing API Status: " + str(paths_status) + "\nRouting API URL:\n" + paths_url)
            print("=================================================")
            print("Directions from " + orig[3] + " to " + dest[3] + " by " + vehicle)
            print("=================================================")
            
            if paths_status == 200:
                miles = (paths_data["paths"][0]["distance"]) / 1000 / 1.61
                km = (paths_data["paths"][0]["distance"]) / 1000
                sec = int(paths_data["paths"][0]["time"] / 1000 % 60)
                min = int(paths_data["paths"][0]["time"] / 1000 / 60 % 60)
                hr = int(paths_data["paths"][0]["time"] / 1000 / 60 / 60)
                
                print("Distance Traveled: {0:.1f} miles / {1:.1f} km".format(miles, km))
                print("Trip Duration: {0:02d}:{1:02d}:{2:02d}".format(hr, min, sec))
                print("=================================================")
                
                for each in range(len(paths_data["paths"][0]["instructions"])):
                    path = paths_data["paths"][0]["instructions"][each]["text"]
                    distance = paths_data["paths"][0]["instructions"][each]["distance"]
                    print("{0} ({1:.1f} km / {2:.1f} miles)".format(path, distance / 1000, distance / 1000 / 1.61))
                
                print("=================================================")
                
                # *** RAG INTEGRATION: Store route information ***
                rag_system.store_route_data(paths_data, orig[3], dest[3], vehicle)
                
                # Ask if user wants AI-enhanced information about this route
                enhance = input("Would you like AI-enhanced information about this route? (y/n): ")
                if enhance.lower() == "y":
                    query = f"Tell me about the route from {orig[3]} to {dest[3]} by {vehicle}"
                    response = rag_system.query(query)
                    print("\n=================================================")
                    print("AI-Enhanced Route Information:")
                    print("=================================================")
                    print(response["answer"])
                    print("=================================================")
            else:
                print("Error message: " + paths_data["message"])
                
        print("*************************************************")

if __name__ == "__main__":
    main()