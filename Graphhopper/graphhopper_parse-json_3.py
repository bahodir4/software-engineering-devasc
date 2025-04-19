import requests
import urllib.parse
import os

route_url = "https://graphhopper.com/api/1/route?"
geocode_url = "https://graphhopper.com/api/1/geocode?"

loc1 = "Washington, D.C."
loc2 = "Baltimore, Maryland"

key = os.getenv("TRACE") 
if not key:
    key = input("Please enter your GraphHopper API key: ")

def geocoding(location, api_key):
    """Geocode a location string to coordinates using GraphHopper API"""
    if not location:
        return 400, "null", "null", "Empty location"
        
    url = geocode_url + urllib.parse.urlencode({"q": location, "limit": "1", "key": api_key})
    print(f"Geocoding API URL for {location}:\n{url}")
    
    try:
        response = requests.get(url)
        json_data = response.json()
        json_status = response.status_code
        
        if json_status == 200 and json_data["hits"]:
            hit = json_data["hits"][0]
            lat = hit["point"]["lat"]
            lng = hit["point"]["lng"]
            name = hit["name"]
            value = hit["osm_value"]
            
            location_parts = [name]
            if "state" in hit:
                location_parts.append(hit["state"])
            if "country" in hit:
                location_parts.append(hit["country"])
                
            new_loc = ", ".join(location_parts)
            print(f"Geocoding result for {new_loc} (Location Type: {value})")
            return json_status, lat, lng, new_loc
        else:
            print(f"No results found for {location}")
            return json_status, "null", "null", location
            
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return 500, "null", "null", location

def get_route(origin, destination, api_key):
    """Get route between two geocoded locations"""
    if origin[0] != 200 or destination[0] != 200:
        return "Cannot calculate route: Invalid coordinates"
        
    op = f"&point={origin[1]},{origin[2]}"
    dp = f"&point={destination[1]},{destination[2]}"
    
    paths_url = route_url + urllib.parse.urlencode({"key": api_key}) + op + dp
    
    try:
        response = requests.get(paths_url)
        paths_status = response.status_code
        paths_data = response.json()
        
        print(f"Routing API Status: {paths_status}\nRouting API URL:\n{paths_url}")
        
        if paths_status == 200:
            route = paths_data["paths"][0]
            distance = route["distance"] / 1000  
            time = route["time"] / (1000 * 60)   
            
            print(f"\nRoute found from {origin[3]} to {destination[3]}:")
            print(f"Distance: {distance:.2f} km")
            print(f"Estimated time: {time:.2f} minutes")
            
            if "instructions" in route:
                print("\nTurn-by-turn directions:")
                for i, instruction in enumerate(route["instructions"]):
                    print(f"{i+1}. {instruction['text']}")
                    
            return paths_data
        else:
            print(f"Error getting route: {paths_data.get('message', 'Unknown error')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None

print("Initial locations:")
orig = geocoding(loc1, key)
dest = geocoding(loc2, key)

print("\nEnter locations to find routes (type 'quit' or 'q' to exit)")
print("=================================================")

while True:
    loc1 = input("\nStarting Location: ")
    if loc1.lower() in ["quit", "q"]:
        break
        
    orig = geocoding(loc1, key)
    
    loc2 = input("Destination: ")
    if loc2.lower() in ["quit", "q"]:
        break
        
    dest = geocoding(loc2, key)
    
    print("=================================================")
    
    if orig[0] == 200 and dest[0] == 200:
        route_data = get_route(orig, dest, key)
    else:
        print("Unable to calculate route due to geocoding errors.")
    
    print("=================================================")

print("Thank you for using the routing service!")