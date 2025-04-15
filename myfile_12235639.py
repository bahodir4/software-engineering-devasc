import json

class MyJson: 
    def __init__(self, json_path):
        self.json_path = json_path
        self.data = None
    
    def read_json(self):
        try:
            with open(self.json_path, 'r', encoding='utf-8') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            print(f"Error: File '{self.json_path}' not found.")
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON in '{self.json_path}'.")
    
    def print_json_data(self):
        if self.data is None:
            print("JSON data not loaded. Please call read_json() first.")
            return

        print("\n--- Parsed JSON Data ---\n")
        for key, value in self.data.items():
            formatted_key = key.replace('_', ' ').capitalize()
            print(f"{formatted_key}: {value}")

if __name__ == "__main__":
    json_file = "myfile.json"
    myjson = MyJson(json_file)
    myjson.read_json()
    myjson.print_json_data()
