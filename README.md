# Firmware Update by Rules

_Python Edition_

Enforce Notecard and Host firmware combinations, and provide rules for when to update Notecard and Host MCU firmware.

Rules in this example can be based on

- Notecard firmware version
- Host MCU firmware version
- Notecard fleet membership

This example assumes the firmware version rule checks and subsequent firmware update requests are invoked by execution of a Notehub route.  That is, this is driven by Notecard event behavior rather than assigning a specific period.

It is worth considering having a periodic version of firmware update checks execute once a day to catch any devices that don't connect frequently, or may have been missed for some reason in addition to the event driven updates.

## Notehub Route Configuration

This example is designed to be invoked by the execution of a Notehub route.  A route can be configured to call any number of endpoints including a RESTful API, AWS Lambda, Google Cloud Function, Azure Cloud, MQTT, etc.

The route can be filtered to only execute if certain conditions are met.  In this example, it will be filtered to the creation of `_session.qo` events, but only on session opening, not session closing.

All of the following configurations can be applied to any of the appropriate Notehub route types.  For specific Route configurations, please consult the Blues documentation.

|Name|Value|Comments|
|---|---|---|
|Fleets|All Fleets|You can filter by fleets if the firmware check and update process only applies to devices in specific fleets|
|Notefiles|Selected Notefiles| |
|Include Other Notefiles|_session.qo| |
|Transform Data|JSONata Expression| |
|JSONata Expression| `($not(body.opened) ? $doNotRoute(): {"device":device, "fleets":fleets})` | Filter to only session opening events, and only provide the necessary data required for the firmware check|
|**For Testing**| |When testing the route setup and configuration, also apply the following|
|Enable this route| off (false) | Will show `(Currently disabled)` on Route UI when set to off|

---
> **❗IMPORTANT**
> 
> Click the "Apply changes" or "Create route" button in order to save the configuration changes

### Testing Routes

It is possible in Notehub to manually route an existing event in Notehub to any route, including a disabled route.

<https://dev.blues.io/notehub/notehub-walkthrough/#manually-routing-events>

By disabling the route, it prevents it from being executed automatically from events generated in Notehub while the route is being tested and developed. But it can still be executed manually using existing event data in Notehub.

## Authentication and Script Environment Configuration

This example script uses the Notehub Project API to gather additional data from a Notehub project and device, as well as sending firmware update requests.

This requires authentication with the Notehub.

This example uses the OAuth method of interacting with Notehub.

### Generating Client ID and Secret

You can generate Client ID and Client Secrets for a given Notehub project in the Notehub Project settings:

<https://dev.blues.io/api-reference/notehub-api/api-introduction/#authentication-with-oauth-bearer-tokens>

### Obtaining Notehub Project UID

Navigate to the `Settings` page for your Notehub project.

Under the `Project information` section, select the copy button next to the value in the `Project UID` field.

### Environment Variables

The best practice is to store the Client ID, Client Secret, and Project UID in system environment variables.

The exact mechanism required for creating the environment variable will vary depending on the deployment system used to execute this example.

You will want to create the following environment variables with the values obtained from the steps above

|Environment Variable|Value|
|---|---|
|NOTEHUB_CLIENT_ID|`<client id obtained above>`|
|NOTEHUB_CLIENT_SECRET|`<client secret obtained above>`|
|NOTEHUB_PROJECT_UID|`<app:xxxxx-xxxx-xxxx-xxxx-xxxxx>`|

> **❗IMPORTANT**
> 
> Do not store these values in source control.

## Request Authorization

This system includes authentication capabilities to secure access to the firmware management endpoints. The `auth.py` module provides comprehensive request authentication using various header formats.

### Supported Authentication Methods

The system supports multiple authentication schemes for maximum flexibility:

1. **Bearer Token** (Recommended)
   ```
   Authorization: Bearer <your-token>
   ```

2. **Direct Token** in Authorization Header
   ```
   Authorization: <your-token>
   ```

3. **API Key Header**
   ```
   x-api-key: <your-token>
   ```

### Authentication Behavior

- **Header Precedence**: The `x-api-key` header takes precedence over the `Authorization` header if both are present
- **Case Insensitive**: All header names are processed case-insensitively (e.g., `AUTHORIZATION`, `X-API-KEY`)
- **Whitespace Handling**: Tokens are automatically trimmed of leading/trailing whitespace
- **Security**: Uses constant-time comparison (`hmac.compare_digest()`) to prevent timing attacks

### Configuration

To enable request authentication, configure your authentication token as an environment variable:

```bash
export AUTH_TOKEN="your-secure-token-here"
```

### Example Usage

#### Using Bearer Token (Recommended)
```bash
curl -X POST https://your-endpoint.com/firmware-check \
  -H "Authorization: Bearer your-secure-token-here" \
  -H "Content-Type: application/json" \
  -d '{"device": "dev:123456", "fleets": ["fleet:abc-def"]}'
```

#### Using API Key Header
```bash
curl -X POST https://your-endpoint.com/firmware-check \
  -H "x-api-key: your-secure-token-here" \
  -H "Content-Type: application/json" \
  -d '{"device": "dev:123456", "fleets": ["fleet:abc-def"]}'
```

### Authentication Errors

The system returns specific error messages for authentication failures:

- `Missing authorization header` - No authentication header provided
- `Empty authorization token` - Authentication header is empty or contains only whitespace
- `Invalid authorization token` - Token doesn't match the expected value
- `Authentication not configured` - Server-side authentication token is not configured
- `Authentication system error` - Internal error during authentication processing


## Rules Configuration

The content of `rules.py` defines the sets of conditions that must be met in order to request an update to a target Notecard or Host firmware version.

The selection of the rules set is made in the invocation of `manage_firmware` function in `main.py`

### Initial Testing

Use the `DEFAULT_RULES` set by importing from `rules.py` in the `main.py` script.

```python
from rules import DEFAULT_RULES
```

Configure the call to `manage_firmware` to use the DEFAULT_RULES set.

```python
manageFirmware(project, deviceUID, fleet, notecardFirmwareVersion, hostFirmwareVersion, rules=DevicesInUpdateFleet)
```

The DEFAULT_RULES will accept any configuration of Fleet, Notecard firmware, and Host MCU firmware.  They will _not_ request any firmware updates of the device to a target version. They will also be identified as `"default"`.

This makes it possible to test the functions and the Notehub route without worrying about accidentally affecting devices in your Notehub project until you are sure all the different components are working.

When executed successfully from a Notehub route, the route should receive a message that the default rule was followed, and that no firmware update requests were made.

### Rules Condition Testing

When developing a set of rules, edit the `rules.py` file.

A rule set is a list of dictionaries, each item in the list defines a set of conditions and target firmware versions.

Each rule has an `id`, a set of `conditions` and `targetVersions`.  _IF_ all of the `conditions` are met for a specific rule, then updates to the firmware versions in the `targetVersions` are requested.

**For testing** rule conditions it is recommended to set the `targetVersions` value to `None`.

When a rule is executed by `manage_firmware`, it will return the rule identifier where the conditions were met.

This enables you to test if rule `conditions` are being met as expected without invoking a firmware update request to the device.

```python
My_Rule_Set = [
    {
        "id":"highest-precedent-rule",
        "conditions":{
            "notecard": "8.1.3.1754",
            "host": "3.1.2",
            "fleet": "fleet:abc-def-ghi-jklmno"
        },
        "targetVersions": None  # Do not request firmware update
    },
    {
        "id":"next-highest-precedent-rule",
        "conditions":{
            "notecard": "7.5.4.345",
            "host": "3.1.1",
            "fleet": "fleet:abc-def-ghi-jklmno"
        },
        "targetVersions":None
    },
    {
        "id":"lowest-precedent-rule",
        "conditions":{
            "notecard": "6.2.3.123",
            "host": "2.1",
            "fleet": "fleet:abc-def-ghi-jklmno"
        },
        "targetVersions":None
    }
]
```

Once you have created your rule set, be sure to import it into `main.py` and include it in the `manage_firmware` function call.

```python
from rules import My_Rule_Set
```

Configure the call to `manage_firmware` to use the My_Rule_Set set.

```python
manageFirmware(project, deviceUID, fleet, notecardFirmwareVersion, hostFirmwareVersion, rules=My_Rule_Set)
```

### Apply Target Firmware to Rules

Once you have verified the rule conditions are executing as expected, you can then configure the `targetVersions` to the appropriate values for each rule.

Notice in this example the highest precedent rule does not have a set of `targetVersions`. This the desired firmware configuration for this fleet. It acts as a guard against the rest of the rules executing. And will not invoke a firmware update request if the device is already using the desired firmware configuration.

```python
My_Rule_Set = [
    {
        "id":"highest-precedent-rule",
        "conditions":{
            "notecard": "8.1.3.1754",
            "host": "3.1.2",
            "fleet": "fleet:abc-def-ghi-jklmno"
        },
        "targetVersions": None  # Do not request firmware update
    },
    {
        "id":"next-highest-precedent-rule",
        "conditions":{
            "notecard": "7.5.4.345",
            "host": "3.1.1",
            "fleet": "fleet:abc-def-ghi-jklmno"
        },
        "targetVersions":{
            "notecard":"8.1.3.1754",
            "host":"3.1.2"
        }
    },
    {
        "id":"lowest-precedent-rule",
        "conditions":{
            "notecard": "6.2.3.123",
            "host": "2.1",
            "fleet": "fleet:abc-def-ghi-jklmno"
        },
        "targetVersions":{
            "notecard":"7.5.4.345",
            "host":"3.1.1"
        }
    }
]
```

## System Implementation Overview

An overview of the behavior of this example is illustrated in the following sequence diagram.

```mermaid
sequenceDiagram
    Notecard->>Notehub: Establish Session
    Notehub->>Notehub: Generate _session.qo
    activate Notehub
    note right of Notehub: Notehub Route
    Notehub->>+Firmware Check: [is session opening] (device id, fleet ids, )
    deactivate Notehub
    opt Notecard needs Update
        Firmware Check ->> Notehub : Notecard Update Request
    end
    opt Host needs Update
        Firmware Check ->> Notehub : Host Update Request
    end
    Firmware Check ->> -Notehub : Success and Rule Executed
    Notecard->>+Notehub: Sync
    Notehub->>-Notecard: Request any Firmware Updates
```

### Notehub Route

The Notehub Route responds to Notehub Events.  In this case, the route is invoked if an event occurs in a specific Notefile, and has the specific value of `"opening":true` in the event body.

If all of the routing conditions are met, it will invoke the route to call the Firmware Check function.  For a general HTTP Route this will be an HTTP request with the POST method.

The purpose of the route is to invoke a check on a Notecard's firmware condition as needed.  The route is designed to filter out calls to the Firmware Check in cases where it's not needed to reduce the number of superfluous calls to the remote procedure.

### Firmware Check

This is the remote procedure that executes the rules check based on the device UID, the device fleet information, and anything else that may be provided by the execution of the Notehub Route.

When checking the device firmware configuration, if the procedure finds there is a rule that requests a firmware update, the procedure will call back to the Notehub to request an update to a specific firmware image.  This is the case for both the Notecard firmware, and the host firmware.

When the Firmware Check procedure is complete, it returns some information back to Notehub about the status of the firmware check.  Was a rule matched?  If so which one? Were any updates requested, and for which firmware type?

## Rules and Matching

A rule set is a list of rules.

Each rule is a python dictionary.
The dictionary fields are listed here with their default values if they are not provided.

```python
{
    "id": "rule-n", # where n is the index of this rule in the list of rules
    "conditions":None,
    "targetVersions":None
}
```

### ID

The value of the `id` field is a string that provides an identifier for the specific rule.  This should be unique for each rule within a rule set.

If an `id` field is not provided, one is automatically generated based on the index of the rule in the rule set.

The `id` is used to indicate which rule has been satisfied by the set of conditions.

### Conditions

Conditions define what must be true for this rule to be satisfied.

If there are no conditions (i.e. the value of `conditions` is `None`), then the rule is always satisfied.

The conditions consist of 3 checks that must all be satisfied in order for the conditions of the rule to be satisfied.

```python
{"notecard": None,
 "host": None,
 "fleet": None
}
```

If any of the above fields are `None` or the field is missing, then that part of the condition is always `True`.

The value of the fields can be:

- a string that must match exactly
- a function that accepts a string

#### Match Condition with String

If the value of a conditions is a string, then in order to satisfy the condition, the value provided for the field must match exactly.  For example, if the value for `"notecard"` is `"8.1.3"` then the condition will only be satisfied if the Notecard firmware version provided for the specific device under test is exactly `"8.1.3"` and will not be satisfied for something like `"8.1.3.17074"`.

#### Match Condition with Function

If the value of a condition is a function, it must be a function that accepts a string as an input.  The value of that string is the appropriate value for the field.  For example, if the conditions were defined as

```python
{"notecard": lambda v: v.startswith("8.1.3"),
 "host": None,
 "fleet": None
}
```

then if the firmware version for the specific device started with `"8.1.3"` the condition would be satisfied.

It does not have to be a lambda function. It can be other functions defined in the `rules.py` file. Or even functions imported to check semantic versions.

### Target Versions

These represent which versions of firmware to which the device should be updated.

If the value is `None`, no updates are requested.

If the value is a dictionary, then it must take the form as follows. Each element is listed with it's default value if the field is omitted.

```python
{
    "notecard":None,
    "host":None
}
```

If the value of a specific field is set to `None` or the field is omitted, then no request will be made to update the device firmware for that field.

### Precedence

The ordering of the rules in a rule set matters.

The rules engine will execute a target version update request for the first rule that is satisfied in the list of rules.

Another way to say this is the rule with the lowest index in the list of rules that is satisfied will make the associated firmware update requests.

If no condition is satisfied, then no firmware update requests will be made.

#### Sequencing Firmware Updates

If a Notecard has both Notecard and Host firmware updates pending, it will _always_ choose to update the Notecard first.

There may be specific cases where this is undesirable. That is, there may be rare cases where the host firmware _must_ be updated prior to updating the Notecard firmware.

Since the rules in a rule set have precedence, it is possible to sequence which firmware update will be made first.

In the following rule configuration, if the Notecard is on LTS version 8, and the host is on version 2, then do nothing.

Otherwise, update the host to version 2, then update the Notecard to version 8.

```python
Update_Host_Before_Notecard = [
    {
        "id":"has-correct-versions",
        "conditions":{
            "notecard":lambda v: majorVersion(v) >= 8,
            "host": lambda v: majorVersion(v) >= 2},
        "targetVersions":None # we don't want any updates.  device is already on an appropriate set of versions.
    },
    {
        "id":"update-host",
        "conditions":{
            "host": lambda v: majorVersion(v) < 2},
        "targetVersions":{
            "host":"2.1.1" # only update the host
        }
    },
    {
        "id":"update-notecard",
        "conditions":None # we're in the last condition at this point. We should only be here if the host firmware is already on version 2+ and the Notecard firmware is < 8
        "targetVersions":{
            "notecard":"8.1.3.17054"
        }
    }

]
```

## Additional Features

The `manage_firmware` function implement a number of features to try and optimize the number of RESTful API requests made to Notehub. As well as protect against updating when the device already has pending updates.

### Fetch Notecard and Host Firmware Versions

If the Notecard and Host firmware versions are not provided for the device via the Notehub route, then the `manage_firmware` function will fetch the values for the device from Notehub.

### Cache Firmware Version Information

Since firmware images and versions available on a Notehub project don't change very frequently, then there's no need to retrieve the same information each time a Notecard connects to Notehub.

Instead the available firmware for a Notehub project is cached (by default of 30 minutes) so that the system only asks for available firmware occasionally.

The advantage of this approach is if the firmware version information changes, and a device fails to request an update to an appropriate version because the cache hasn't updated yet, it will check again the next time the device establishes a connection to Notehub.  Eventually the cache will update, when the device connects to Notehub it will be able to proceed using the updated cache information.

### Return if Firmware Update is Pending

If a device already has a firmware update pending for either the Notecard or the Host MCU, the function will return.  It won't execute any of the rule checks to see if a firmware update is needed.

There is some risk to this approach, as a change to the update rules will not propagate to devices that have pending updates until the pending update has completed or the pending update is cancelled.

It's worth considering updating this procedure to check to see if the pending update matches the results of the rules prior to making any firmware update requests to Notehub.

## System Details

### Full Behavior Model

In addition to the general behavior model described above, there are some additional behaviors that this example provides to help make this system robust.

The sequence of behaviors is captured in the following sequence diagram

```mermaid
sequenceDiagram
    Notecard->>Notehub: Establish Session
    Notehub->>Notehub: Generate _session.qo
    Notehub->>+Firmware Check: [is session opening] (device id, fleet ids, )
    opt Session Token Expired
        Firmware Check ->> Notehub: Request token (client ID, secret)
        Notehub ->> Firmware Check: Session token
    end
    opt Missing Notecard Firmware Version
        Firmware Check ->> Notehub: Request Firmware Version (device ID, projectUID)
        Notehub ->> Firmware Check: Firmware Version
    end
    opt Missing Host Firmware Version
        Firmware Check ->> Notehub: Request Firmware Version (device ID, projectUID)
        Notehub ->> Firmware Check: Firmware Version
    end
    opt Notecard needs Update
        Firmware Check ->> Notehub : Notecard Update Request
    end
    opt Host needs Update
        Firmware Check ->> Notehub : Host Update Request
    end
    Firmware Check ->> -Notehub : Status and Rule Executed
    Notecard->>+Notehub: Sync
    Notehub->>-Notecard: Request any Firmware Updates
```
