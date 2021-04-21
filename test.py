import json

file = open("./last_read.json")
content = file.read()
print(content)

json = json.loads(file)
print(json)
