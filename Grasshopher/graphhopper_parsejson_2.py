import requests
import urllib.parse 
geocode_url = "https://graphhopper.com/api/1/geocode?"
route_url = "https://graphhopper.com/api/1/route?"
loc1 = "Washington, D.C."
loc2 = "Baltimore, Maryland"
key = "f7044f43-46b9-46cb-a4cb-22a25f99a973" 
url = geocode_url + urllib.parse.urlencode({"q":loc1, "limit": "1", "key":key}) 
replydata = requests.get(url)
json_data = replydata.json()
json_status = replydata.status_code
print(json_data)
json_status = replydata.status_code
if json_status == 200:
 print("Geocoding API URL for " + loc1 + ":\n" + url) 
import urllib.parse
import requests

def geocoding(location, key):
    geocode_url = "https://graphhopper.com/api/1/geocode?"
    url = geocode_url + urllib.parse.urlencode({
        "q": location,
        "limit": "1",
        "key": key
    })

    replydata = requests.get(url)
    json_status = replydata.status_code
    print("Geocoding API URL for " + location + ":\n" + url)

    if json_status == 200:
        json_data = replydata.json()
        lat = json_data["hits"][0]["point"]["lat"]
        lng = json_data["hits"][0]["point"]["lng"]
    else:
        lat = "null"
        lng = "null"

    return json_status, lat, lng
