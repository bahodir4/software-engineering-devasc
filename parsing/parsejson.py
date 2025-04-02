import json
import yaml

with open('myfile_12214739.json', 'r') as json_file:
    ourjson = json.load(json_file)

print(ourjson)

print("The access token is: {}".format(ourjson['access_token']))
print("The token expires in {} seconds.".format(ourjson['expires_in']))
print("\nParsed by: Sarvar Akimov (12214739)")
print("\n\n---")
print(yaml.dump(ourjson))
