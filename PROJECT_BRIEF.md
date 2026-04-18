# Child Scheduler – Project Brief

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

- Hubitat is **execution engine only**
- AWS is **source of truth + scheduler**
- No inbound access to home network
- Backend compiles schedule → Hubitat executes only
- Full-replace model for schedule config (simplifies logic)
- Broken references handled explicitly and surfaced to user

---

## Hubitat Capabilities (Validated)

- Custom app can call external HTTPS APIs
- Can schedule one-time executions locally
- Can invoke Rule Machine rules via RMUtils
- Can execute:
  - `rule` → Rule Machine
  - `speech` → `device.speak(text)`
  - `notify` → `device.deviceNotification(text)`
- Can expose:
  - selected Rule Machine rules (filtered)
  - selected speech devices
  - selected notification devices

---

## Action Types

### 1. Rule
- Executes a Rule Machine rule
- Parameter:
  - `targetId: "rule:<id>"`

### 2. Speech
- Sends text to a speech-capable device
- Parameters:
  - `targetId: "speechTarget:<id>"`
  - `text`

### 3. Notify
- Sends text notification
- Parameters:
  - `targetIds: ["notifyDevice:<id>", ...]`
  - `text`

### 4. Broken Reference
- Represents invalid/missing action
- Hubitat will notify user

---

## Action Catalog

### Owned by Hubitat
Hubitat builds and pushes catalog to AWS.

### Contents
- action definitions
- available resources:
  - rule actions (filtered by prefix, e.g. "ZCSA")
  - speech targets
  - notify devices

### Key Properties
- `resourceId` format:
  - `rule:<id>`
  - `speechTarget:<id>`
  - `notifyDevice:<id>`

---

## Schedule Model

### Schedule Definition (DEF)
Reusable rule describing:
- when something should happen
- what action to run

Fields:
- `scheduleId`
- `name`
- `enabled`
- `daysOfWeek`
- `timeMode`:
  - `absolute` → uses `baseTime`
  - `relative` → uses `relativeToScheduleId` + `offsetMinutes`
- `actionType`
- `parameters`

---

### Day Config (DAY)
Overrides for specific dates:

Fields:
- `date`
- `schoolDay`
- `notes`
- `overrides`:
  - enable/disable schedule
  - override time

---

### Compiled Events (EVT)
Fully resolved execution events:

Fields:
- `eventId`
- `date`
- `time`
- `actionType`
- `parameters`
- `sourceScheduleId`

---

### Broken References (BROKEN)
Events that cannot be executed:

Fields:
- `eventId`
- `date`
- `time` (optional)
- `message`
- `originalLabel`
- `sourceScheduleId`

---

## DynamoDB Tables

### 1. ActionCatalogs

**Primary Key**
- `hubId` (String)

**Purpose**
- Stores latest action catalog per hub

---

### 2. Schedules

**Primary Key**
- `hubId` (String)
- `itemKey` (String)

**Item Types**
- `META`
- `DEF#<scheduleId>`
- `DAY#<YYYY-MM-DD>`
- `EVT#<date>#<time>#<eventId>`
- `BROKEN#<date>#<eventId>`

---

## API Endpoints

### Hubitat Endpoints

#### POST /hubitat/action-catalog
- Hubitat pushes available actions/resources
- Writes to `ActionCatalogs`

#### GET /hubitat/schedule
- Hubitat pulls compiled schedule
- Reads:
  - META
  - EVT
  - BROKEN

---

### Web UI Endpoints

#### GET /catalog
- Returns action catalog for UI
- Reads `ActionCatalogs`

#### GET /schedule/config
- Returns editable schedule + preview
- Reads:
  - META
  - DEF
  - DAY
  - EVT (preview)
  - BROKEN

#### PUT /schedule/config
- Saves config and compiles schedule
- Writes:
  - META
  - DEF
  - DAY
  - EVT
  - BROKEN

---

## Compiler Responsibilities

### Inputs
- schedule definitions
- day configs
- action catalog

### Outputs
- compiled events (EVT)
- broken references (BROKEN)

---

### Rules

#### 1. Compile window
- Next 7 days only

#### 2. Schedule selection
- match day-of-week
- apply overrides

#### 3. Time resolution
- absolute → baseTime or override
- relative → dependency + offset
- detect circular dependencies

#### 4. Action validation
- verify resource exists in catalog
- verify correct type
- verify required parameters

#### 5. Broken handling
- invalid targets → BROKEN item
- missing dependencies → BROKEN item
- circular dependencies → BROKEN item

---

## Authentication

### Hubitat
- Header: `X-Hubitat-Token`

### Web UI
- Cognito JWT

---

## Repository Structure

```text
child-scheduler/
  PROJECT_BRIEF.md
  TASKS.md

  backend/
    shared/
    functions/

  ui/
    src/

  hubitat/
    ChildSchedulerHub.groovy

  docs/
