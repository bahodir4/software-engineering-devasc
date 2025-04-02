import json

# my-json class
class MyJson: 
    def __init__(self, json_path):
        self.json_path = json_path
        self.data = None
    
    # method -> reading json file data
    def read_json(self):
        with open(self.json_path, 'r') as file:
            self.data = json.load(file)
    
    # method -> printing json file data
    def printJsonData(self):
        if self.data is None:
            print("JSON data not loaded. Please call read_json() first.")
            return

        print("\n\n--- Parsed JSON Data ---\n")
        for key, value in self.data.items():
            print(f"{key.capitalize().replace('_', ' ')}: {value}")

# creating an object
myjson = MyJson("./myfile_12225254.json")
myjson.read_json()
myjson.printJsonData()
