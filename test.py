import json

file = open("./last_read.json", 'w+')
content = file.read()
print(content)

json = json.loads(content)
print(json)
