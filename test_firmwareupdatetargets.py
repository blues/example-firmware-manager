
import pytest
from unittest.mock import MagicMock
from manage_firmware import getFirmwareUpdateTargets

def test_rule_ids():
    rules = [{"id":"my-id", "conditions":{"fleet":"my-fleet-1"}}, {"conditions":{"fleet":"my-fleet-2"}}]

    (r, _) = getFirmwareUpdateTargets("my-fleet-1",None, None, rules=rules)
    assert r == "my-id"

    (r, _) = getFirmwareUpdateTargets("my-fleet-2",None, None, rules=rules)
    assert r == "rule-2"


def test_rules_all_none():
    rules = {"id":"my-rule", "conditions":None, "targetVersions":None}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=None, rules=rules)

    assert v is None


def test_rules_notecard_rule_string():
    currentVersion = "notecard_version_info"
    targetVersion = "new_notecard_version"
    rules = {"conditions":{"notecard":currentVersion}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)

    assert v == targetVersion
    

    targetVersion = None
    rules = {"conditions":{"notecard":currentVersion}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)

    assert v is None

    targetVersion = "new_notecard_version"
    rules = {"conditions":{"notecard":currentVersion}, "targetVersions":{"notecard":targetVersion}}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)

    assert v.get("notecard") == targetVersion

    targetVersion = "new_host_version"
    rules = {"conditions":{"notecard":currentVersion}, "targetVersions":{"host":targetVersion}}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)

    assert v.get("host") == targetVersion
    assert v.get("notecard") is None


def test_rules_host_rule_string():
    currentVersion = "host_version_info"
    targetVersion = "new_host_version"
    rules = {"conditions":{"host":currentVersion}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)

    assert v == targetVersion

    targetVersion = None
    rules = {"conditions":{"host":currentVersion}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)

    assert v is None

    targetVersion = "new_host_version"
    rules = {"conditions":{"host":currentVersion}, "targetVersions":{"host":targetVersion}}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)

    assert v.get("host") == targetVersion

    targetVersion = "new_notecard_version"
    rules = {"conditions":{"host":currentVersion}, "targetVersions":{"notecard":targetVersion}}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)

    assert v.get("notecard") == targetVersion
    assert v.get("host") is None

def test_rules_notecard_host_fleet_rule_string():

    currentHostVersion = "host_version_info"
    currentNotecardVersion = "notecard_version_info"
    fleetUID = "my-fleet-uid"
    targetVersion = "test-target-version"
    rules = {"conditions":{"host":currentHostVersion,"notecard":currentNotecardVersion,"fleet":fleetUID}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=currentNotecardVersion, hostVersion=currentHostVersion, rules=rules)

    assert v == targetVersion

    (_, v) = getFirmwareUpdateTargets(fleetUID=fleetUID + "-is-different", notecardVersion=currentNotecardVersion, hostVersion=currentHostVersion, rules=rules)

    assert v is None

    (_, v) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=currentNotecardVersion + "-is-different", hostVersion=currentHostVersion, rules=rules)

    assert v is None

    (_, v) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=currentNotecardVersion, hostVersion=currentHostVersion + "-is-different", rules=rules)

    assert v is None


def test_rules_notecard_rule_is_function_returning_True():
    c = MagicMock()
    c.return_value = True

    currentVersion = "notecard_version_info"
    targetVersion = "test-target-version"
    rules = {"conditions":{"notecard":c}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)

    assert v == targetVersion
    c.assert_called_once_with(currentVersion)

def test_rules_notecard_rule_is_function_returning_False():
    c = MagicMock()
    c.return_value = False

    currentVersion = "notecard_version_info"
    targetVersion = "test-target-version"
    rules = {"conditions":{"notecard":c}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)

    assert v is None
    c.assert_called_once_with(currentVersion)

def test_rules_host_rule_is_function_returning_True():
    c = MagicMock()
    c.return_value = True

    currentVersion = "host_version_info"
    targetVersion = "test-target-version"
    rules = {"conditions":{"host":c}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)

    assert v == targetVersion
    c.assert_called_once_with(currentVersion)

def test_rules_host_rule_is_function_returning_False():
    c = MagicMock()
    c.return_value = False

    currentVersion = "host_version_info"
    targetVersion = "test-target-version"
    rules = {"conditions":{"host":c}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)

    assert v is None
    c.assert_called_once_with(currentVersion)



def test_rules_fleet_rule_is_function_returning_True():
    c = MagicMock()
    c.return_value = True

    fleetUID = "my-fleet-uid"
    targetVersion = "test-target-version"
    rules = {"conditions":{"fleet":c}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=None, hostVersion=None, rules=rules)

    assert v == targetVersion
    c.assert_called_once_with(fleetUID)

def test_rules_fleet_rule_is_function_returning_False():
    c = MagicMock()
    c.return_value = False

    fleetUID = "my-fleet-uid"
    targetVersion = "test-target-version"
    rules = {"conditions":{"fleet":c}, "targetVersions":targetVersion}

    (_, v) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=None, hostVersion=None, rules=rules)

    assert v is None
    c.assert_called_once_with(fleetUID)


def test_rules_precedence():

    ncTarget = "notecard-target-version"
    hostTarget = "host-target-version"

    fleetUID = "my-fleet-uid"
    desiredNotecardVersion = "desired-notecard-version"
    desiredHostVersion = "desired-host-version"
    rules = [
              {"conditions":{
                  "fleet": fleetUID, 
                  "notecard":desiredNotecardVersion, 
                  "host": desiredHostVersion
                  },
                "targetVersions":None,
                "id": "have-desired-versions"
              },
              {"conditions":{
                  "fleet": fleetUID, 
                  "notecard":"un" + desiredNotecardVersion, 
                  "host": desiredHostVersion
                  },
                "targetVersions":ncTarget,
                "id": "correct-host-incorrect-notecard"
              },
              {"conditions":{
                  "fleet": fleetUID
                  },
                "targetVersions":hostTarget,
                "id": "all-remaining-options"
              }
    ]

    (r, v) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion="un" + desiredNotecardVersion, hostVersion="un" + desiredHostVersion, rules=rules)

    assert v == hostTarget
    assert r == "all-remaining-options"

    (r, v) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion="un" + desiredNotecardVersion, hostVersion=desiredHostVersion, rules=rules)

    assert v == ncTarget
    assert r == "correct-host-incorrect-notecard"

    (r, v) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=desiredNotecardVersion, hostVersion=desiredHostVersion, rules=rules)

    assert v is None
    assert r == "have-desired-versions"
