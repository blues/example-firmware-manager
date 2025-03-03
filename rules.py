DEFAULT_RULES = [{"id":"default",
                  "conditions":None,
                  "targetVersions": None}]

def majorVersion(s):
    return int(s.split(".")[0])

def minorVersion(s):
    return int(s.split(".")[1])

DevicesInUpdateFleet = [
    {
        "conditions":{
            "notecard":lambda v: v.startswith("7.5.1.")
            },
        "targetVersions":{"notecard":"7.5.2.17004"}
    },
    {
        "conditions":{
            "notecard": lambda v: majorVersion(v) < 8, 
            "fleet":"fleet:50b4f0ee-b8e4-4c9c-b321-243ff1f9e487"},
        "targetVersions":{"notecard":"8.1.3.17044"}
    }
]