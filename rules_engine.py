"""
Rules Engine for Firmware Update Management

This module provides the core rules evaluation logic for determining when and how
to update firmware based on device conditions and rule configurations.

The rules engine is independent of external dependencies like Notehub APIs,
making it easily testable and reusable.
"""

# Default rule set that accepts any configuration but doesn't request updates
DEFAULT_RULES = [{"id": "default", "conditions": None, "target_versions": None}]


def getFirmwareUpdateTargets(device_data, rules=DEFAULT_RULES):
    """
    Determine firmware update targets based on device conditions and rules.
    
    This function evaluates a set of rules against the current device state
    and returns the first matching rule's target firmware versions.
    
    Args:
        device_data (dict): Dictionary containing device field values for rule evaluation
        rules (list or dict): Rule set to evaluate against device conditions
        
    Returns:
        tuple: (rule_id, target_versions)
            - rule_id (str): ID of the matched rule, None if no match
            - target_versions: Target firmware versions from matched rule, None if no updates
            
    Rule Format:
        Each rule is a dictionary with:
        - id (str, optional): Rule identifier, auto-generated if missing
        - conditions (dict, optional): Conditions that must be met on arbitrary fields
            - Any field name can be used as a key with conditions:
                - str: Exact match required
                - callable: Function called with device value, returns bool
                - None: Always matches (condition ignored)
        - target_versions: Target firmware versions if conditions match
            - Can be None (no updates), string, or dict with firmware type keys
            
    Notes:
        - Rules are evaluated in order, first match wins (precedence by list position)
        - If condition is None or missing, it's considered always true
        - If condition is callable, it's called with the device value
        - If condition is string, it must match exactly
        - If all conditions in a rule match, that rule's target_versions are returned
        
    Example:
        device_data = {
            "notecard": "8.1.2",
            "host": "3.1.1", 
            "fleet": "fleet:prod",
            "deviceType": "sensor",
            "location": "outdoor"
        }
        
        rules = [
            {
                "id": "desired-state",
                "conditions": {"notecard": "8.1.3", "host": "3.1.2", "fleet": "fleet:prod"},
                "target_versions": None  # No updates needed
            },
            {
                "id": "outdoor-sensors-update", 
                "conditions": {"fleet": "fleet:prod", "deviceType": "sensor", "location": "outdoor"},
                "target_versions": {"notecard": "8.1.3", "host": "3.1.2"}
            }
        ]
    """
    
    def resolve_field_value(field_name):
        """
        Resolve field value from device_data, supporting dot notation for nested objects.
        
        Args:
            field_name (str): Field name, potentially with dot notation (e.g., "firmware_notecard.version")
            
        Returns:
            The resolved field value, or None if the field path cannot be found
            
        Examples:
            resolve_field_value("fleet") -> device_data["fleet"]
            resolve_field_value("firmware_notecard.version") -> device_data["firmware_notecard"]["version"]
            resolve_field_value("missing.field") -> None
        """
        if '.' not in field_name:
            # Simple field lookup
            return device_data.get(field_name)
        
        # Dot notation - traverse nested object
        parts = field_name.split('.')
        current_value = device_data.get(parts[0])
        
        if current_value is None:
            return None
            
        # Navigate through the nested structure
        for part in parts[1:]:
            if not isinstance(current_value, dict):
                return None  # Can't traverse further - not a dict
            current_value = current_value.get(part)
            if current_value is None:
                return None  # Field not found in nested structure
                
        return current_value

    def match_condition(value, condition):
        """
        Check if a device value matches a rule condition.
        
        Args:
            value: The device value to check
            condition: The rule condition (string, or callable)
            
        Returns:
            bool: True if condition matches, False otherwise
        """
        
        if callable(condition):
            # Function condition - call with device value
            return condition(value)
        
        # String condition - exact match required
        return value == condition
    
    def checkConditions(conditions):
        if conditions is None:
            return True
        
        for field_name, condition_value in conditions.items():
            device_field_value = resolve_field_value(field_name)
            if not match_condition(device_field_value, condition_value):
                return False
            
        return True

    # Normalize rules to list format
    if not isinstance(rules, list):
        rules = [rules]

    # Evaluate each rule in order
    for i, rule in enumerate(rules):
        conditions = rule.get("conditions", None)
        rule_id = rule.get("id", f"rule-{i + 1}")
        target_versions = rule.get("target_versions", None)
        
        # Check all conditions must be met (iterate over arbitrary fields)
        all_conditions_match = checkConditions(conditions)

        # If all conditions match, return this rule's targets
        if all_conditions_match:
            return (rule_id, target_versions)

    # No rules matched
    return (None, None)


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
