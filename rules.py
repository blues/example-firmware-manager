DEFAULT_RULES = [{"id":"default",
                  "conditions":None,
                  "target_versions": None}]

def majorVersion(s):
    return int(s.split(".")[0])

def minorVersion(s):
    return int(s.split(".")[1])

def fleetsContain(f):
    return lambda fleet_list: fleet_list and f in fleet_list

DevicesInUpdateFleet = [
    {
        "conditions":{
            "firmware_notecard.ver_major": 7,
            "firmware_notecard.ver_minor": 5,
            "firmware_notecard.ver_patch": 1
            },
        "target_versions":{"notecard":"7.5.2.17004"}
    },
    {
        "conditions":{
            "firmware_notecard.ver_major": lambda major: major is not None and major < 8, 
            "fleets": fleetsContain("fleet:50b4f0ee-b8e4-4c9c-b321-243ff1f9e487")
        },
        "target_versions":{"notecard":"8.1.3.17044"}
    }
]


#MIT License

#Copyright (c) 2025 Blues Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
