# PROJECT_BRIEF.md

## Goal

Build a cloud-hosted scheduling system to manage children’s wake-up times, bedtimes, and reminders.

- UI: Web application (hosted in AWS)
- Backend: AWS Lambda + DynamoDB
- Execution: Hubitat (local) via custom Groovy app
- No inbound connections to local network
- Hubitat pulls schedule and executes locally

---

## High-Level Architecture

### Flow

1. Hubitat → AWS
   - Push action catalog (available actions/devices)
   - Pull compiled schedule (next 7 days)

2. User → AWS UI
   - Configure schedules via web UI
   - Save configuration to backend
   - Backend compiles schedule

3. AWS → Hubitat
   - Hubitat periodically pulls compiled schedule
   - Executes events locally

---

## Key Design Principles

- Hubitat is execution engine only
- AWS is source of truth + scheduler
- No inbound access to home network
- Backend compiles schedule → Hubitat executes only
- Full-replace model for schedule config
- Broken references explicitly surfaced

---

## Hubitat Capabilities (Validated)

- Custom app can call external HTTPS APIs
- Can schedule one-time executions locally
- Can invoke Rule Machine rules via RMUtils
- Can execute:
  - rule → Rule Machine
  - speech → device.speak(text)
  - notify → device.deviceNotification(text)
- Can expose:
  - selected Rule Machine rules
  - selected speech devices
  - selected notification devices

---

## Action Types

### Rule
- Executes Rule Machine rule
- targetId: "rule:<id>"

### Speech
- targetId: "speechTarget:<id>"
- text

### Notify
- targetIds: ["notifyDevice:<id>", ...]
- text

### Broken Reference
- Represents invalid/missing action
- Hubitat notifies user

---

## Action Catalog

Owned by Hubitat.

Includes:
- actionDefinitions
- resources:
  - rule:<id>
  - speechTarget:<id>
  - notifyDevice:<id>

---

## Schedule Model

### Schedule Definition (DEF)

- scheduleId
- name
- enabled
- daysOfWeek
- timeMode (absolute | relative)
- baseTime
- relativeToScheduleId
- offsetMinutes
- actionType
- parameters

---

### Day Config (DAY)

- date
- schoolDay
- notes
- overrides:
  - enabled
  - timeOverride

---

### Compiled Events (EVT)

- eventId
- date
- time
- actionType
- parameters
- sourceScheduleId

---

### Broken References (BROKEN)

- eventId
- date
- message
- originalLabel
- sourceScheduleId

---

## DynamoDB Tables

### ActionCatalogs

- PK: hubId (String)

---

### Schedules

- PK: hubId (String)
- SK: itemKey (String)

Item types:
- META
- DEF#<scheduleId>
- DAY#<date>
- EVT#<date>#<time>#<eventId>
- BROKEN#<date>#<eventId>

---

## API Endpoints

### Hubitat

POST /hubitat/action-catalog  
GET /hubitat/schedule  

### UI

GET /catalog  
GET /schedule/config  
PUT /schedule/config  

---

## Compiler Responsibilities

- Compile next 7 days
- Resolve absolute and relative times
- Apply overrides
- Validate actions against catalog
- Detect broken references
- Output EVT and BROKEN items

---

## Authentication

- Hubitat: X-Hubitat-Token
- UI: Cognito JWT

---

## Repo Structure

    child-scheduler/
      PROJECT_BRIEF.md
      TASKS.md

      backend/
      ui/
      hubitat/
      docs/

---

## Implementation Plan

1. Action catalog endpoint
2. Catalog retrieval
3. Schedule read endpoint
4. Compiler
5. Schedule write endpoint
6. Hubitat schedule endpoint

---

## Current Status

- Hubitat prototype complete and validated
- Scheduling, rule execution, speech, notify all working
- AWS backend not yet implemented
- UI not yet implemented

---

## Next Step

Use Codex to begin backend implementation starting with:

- POST /hubitat/action-catalog
- GET /catalog
