"""
Rules Engine for Firmware Update Management

This module provides the core rules evaluation logic for determining when and how
to update firmware based on device conditions and rule configurations.

The rules engine is independent of external dependencies like Notehub APIs,
making it easily testable and reusable.
"""

# Default rule set that accepts any configuration but doesn't request updates
DEFAULT_RULES = [{"id": "default", "conditions": None, "targetVersions": None}]


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
        - targetVersions: Target firmware versions if conditions match
            - Can be None (no updates), string, or dict with firmware type keys
            
    Notes:
        - Rules are evaluated in order, first match wins (precedence by list position)
        - If condition is None or missing, it's considered always true
        - If condition is callable, it's called with the device value
        - If condition is string, it must match exactly
        - If all conditions in a rule match, that rule's targetVersions are returned
        
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
                "targetVersions": None  # No updates needed
            },
            {
                "id": "outdoor-sensors-update", 
                "conditions": {"fleet": "fleet:prod", "deviceType": "sensor", "location": "outdoor"},
                "targetVersions": {"notecard": "8.1.3", "host": "3.1.2"}
            }
        ]
    """
    
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
            device_field_value = device_data.get(field_name)
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
        target_versions = rule.get("targetVersions", None)
        
        # Check all conditions must be met (iterate over arbitrary fields)
        all_conditions_match = checkConditions(conditions)

        # If all conditions match, return this rule's targets
        if all_conditions_match:
            return (rule_id, target_versions)

    # No rules matched
    return (None, None)