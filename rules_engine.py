"""
Rules Engine for Firmware Update Management

This module provides the core rules evaluation logic for determining when and how
to update firmware based on device conditions and rule configurations.

The rules engine is independent of external dependencies like Notehub APIs,
making it easily testable and reusable.
"""

# Default rule set that accepts any configuration but doesn't request updates
DEFAULT_RULES = [{"id": "default", "conditions": None, "targetVersions": None}]


def getFirmwareUpdateTargets(fleetUID, notecardVersion, hostVersion, rules=DEFAULT_RULES):
    """
    Determine firmware update targets based on device conditions and rules.
    
    This function evaluates a set of rules against the current device state
    (fleet membership, firmware versions) and returns the first matching rule's
    target firmware versions.
    
    Args:
        fleetUID (str): The fleet UID the device belongs to
        notecardVersion (str): Current Notecard firmware version  
        hostVersion (str): Current host MCU firmware version
        rules (list or dict): Rule set to evaluate against device conditions
        
    Returns:
        tuple: (rule_id, target_versions)
            - rule_id (str): ID of the matched rule, None if no match
            - target_versions: Target firmware versions from matched rule, None if no updates
            
    Rule Format:
        Each rule is a dictionary with:
        - id (str, optional): Rule identifier, auto-generated if missing
        - conditions (dict, optional): Conditions that must be met
            - notecard (str or callable): Notecard version condition
            - host (str or callable): Host version condition  
            - fleet (str or callable): Fleet membership condition
        - targetVersions: Target firmware versions if conditions match
            - Can be None (no updates), string, or dict with 'notecard'/'host' keys
            
    Notes:
        - Rules are evaluated in order, first match wins (precedence by list position)
        - If condition is None or missing, it's considered always true
        - If condition is callable, it's called with the device value
        - If condition is string, it must match exactly
        - If all conditions in a rule match, that rule's targetVersions are returned
        
    Example:
        rules = [
            {
                "id": "desired-state",
                "conditions": {"notecard": "8.1.3", "host": "3.1.2", "fleet": "fleet:prod"},
                "targetVersions": None  # No updates needed
            },
            {
                "id": "update-needed", 
                "conditions": {"fleet": "fleet:prod"},
                "targetVersions": {"notecard": "8.1.3", "host": "3.1.2"}
            }
        ]
    """
    
    def match_condition(value, condition):
        """
        Check if a device value matches a rule condition.
        
        Args:
            value: The device value to check
            condition: The rule condition (None, string, or callable)
            
        Returns:
            bool: True if condition matches, False otherwise
        """
        if condition is None:
            # No condition means always match
            return True
        
        if callable(condition):
            # Function condition - call with device value
            return condition(value)
        
        # String condition - exact match required
        return value == condition
    
    # Normalize rules to list format
    if not isinstance(rules, list):
        rules = [rules]

    # Evaluate each rule in order
    for i, rule in enumerate(rules):
        conditions = rule.get("conditions", None)
        rule_id = rule.get("id", f"rule-{i + 1}")
        target_versions = rule.get("targetVersions", None)
        
        # If no conditions, rule always matches
        if conditions is None:
            return (rule_id, target_versions)
        
        # Check all conditions must be met
        notecard_match = match_condition(notecardVersion, conditions.get("notecard"))
        host_match = match_condition(hostVersion, conditions.get("host"))
        fleet_match = match_condition(fleetUID, conditions.get("fleet"))
        
        # If all conditions match, return this rule's targets
        if notecard_match and host_match and fleet_match:
            return (rule_id, target_versions)

    # No rules matched
    return (None, None)