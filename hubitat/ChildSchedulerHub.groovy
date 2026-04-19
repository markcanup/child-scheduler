import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import hubitat.helper.RMUtils

definition(
    name: "Child Scheduler Hub",
    namespace: "markcanup",
    author: "OpenAI",
    description: "Hubitat-side scheduler runtime for AWS-hosted child schedule management",
    category: "Convenience",
    iconUrl: "",
    iconX2Url: "",
    singleThreaded: true
)

preferences {
    page(name: "mainPage", title: "Child Scheduler Hub", install: true, uninstall: true) {
        section("AWS connection") {
            input "awsBaseUrl", "text", title: "AWS Base URL", required: true
            input "hubId", "text", title: "Hub ID", required: true
            input "hubitatToken", "password", title: "Hubitat shared secret (X-Hubitat-Token)", required: true
        }

        section("Rule Machine action discovery") {
            input "ruleFilterMode", "enum",
                title: "Rule filter mode",
                required: true,
                defaultValue: "startsWith",
                options: [
                    "startsWith": "Starts with",
                    "contains": "Contains"
                ]

            input "ruleFilterText", "text",
                title: "Rule filter text",
                required: true,
                defaultValue: "ZCSA"
        }

        section("Allowed speech targets") {
            input "allowedSpeechTargets", "capability.speechSynthesis",
                title: "Speech target devices",
                multiple: true,
                required: false
        }

        section("Allowed notify devices") {
            input "allowedNotifyDevices", "capability.notification",
                title: "Notification devices",
                multiple: true,
                required: false

            input "adminNotifyDevices", "capability.notification",
                title: "Admin notification devices",
                multiple: true,
                required: false
        }

        section("Sync behavior") {
            input "scheduleDaysToPull", "number",
                title: "Days of schedule to pull",
                required: true,
                defaultValue: 7

            input "catalogPushOnInitialize", "bool",
                title: "Push catalog on initialize",
                required: true,
                defaultValue: false

            input "schedulePullOnInitialize", "bool",
                title: "Pull schedule on initialize",
                required: true,
                defaultValue: false

            input "sendBrokenReferenceNotifications", "bool",
                title: "Notify on broken references",
                required: true,
                defaultValue: true
        	
            input "useMockCatalogPush", "bool",
                title: "Use mock catalog push instead of HTTP",
                required: true,
                defaultValue: false

            input "useMockSchedulePull", "bool",
                title: "Use mock schedule pull instead of HTTP",
                required: true,
                defaultValue: false
        }
        

        section("Manual actions") {
            input "btnPushCatalog", "button", title: "Push action catalog now"
            input "btnPullSchedule", "button", title: "Pull schedule now"
            input "btnClearSchedule", "button", title: "Clear all scheduled events"
            href name: "showStateHref", title: "Show scheduler state", page: "statusPage", description: "View current state and pending events"
        }
    }

    page(name: "pushCatalogPage") {
        //pushActionCatalog()
        section("Push action catalog") {
            paragraph "Use the button on the main page instead."
        }
    }

    page(name: "pullSchedulePage") {
        //pullScheduleAndApply()
        section("Pull schedule") {
            paragraph "Use the button on the main page instead."
        }
    }

    page(name: "statusPage") {
        section("Current state") {
            paragraph "Last catalog push: ${state.lastCatalogPushTime ?: 'none'}"
            paragraph "Last catalog push status: ${state.lastCatalogPushStatus ?: 'none'}"
            paragraph "Last catalog push URL: ${state.lastCatalogPushUrl ?: 'none'}"
            paragraph "Last catalog push request bytes: ${state.lastCatalogPushRequestBytes ?: 'none'}"
            paragraph "Last catalog push response body: ${state.lastCatalogPushResponseBody ?: 'none'}"
            paragraph "Last catalog push error: ${state.lastCatalogPushError ?: 'none'}"
            paragraph "Last schedule pull: ${state.lastSchedulePullTime ?: 'none'}"
            paragraph "Last schedule pull status: ${state.lastSchedulePullStatus ?: 'none'}"
            paragraph "Last schedule pull URL: ${state.lastSchedulePullUrl ?: 'none'}"
            paragraph "Last schedule pull response body: ${state.lastSchedulePullResponseBody ?: 'none'}"
            paragraph "Last schedule pull error: ${state.lastSchedulePullError ?: 'none'}"
            paragraph "Last pulled event count: ${state.lastSchedulePullEventCount ?: 0}"
            paragraph "Last schedule version: ${state.lastScheduleVersion ?: 'none'}"
            paragraph "Pending scheduled events count: ${state.pendingEvents?.size() ?: 0}"
            paragraph "Pending scheduled events: ${state.pendingEvents ?: []}"
            paragraph "Broken reference notifications sent: ${state.brokenReferenceKeys ?: []}"
        }
    }

    page(name: "clearSchedulePage") {
        //clearScheduledEvents()
        section("Clear scheduled events") {
            paragraph "Use the button on the main page instead."
        }
    }
}

def installed() {
    log.info "Installed ${app.label}"
    initialize()
}

def updated() {
    log.info "Updated ${app.label}"
    unschedule()
    initialize()
}

def initialize() {
    log.info "Initializing ${app.label}"

    if (catalogPushOnInitialize) {
        pushActionCatalog()
    }

    if (schedulePullOnInitialize) {
        pullScheduleAndApply()
    }
}

def appButtonHandler(String btn) {
    log.info "Button pressed: ${btn}"

    if (btn == "btnPushCatalog") {
        pushActionCatalog()
    } else if (btn == "btnPullSchedule") {
        pullScheduleAndApply()
    } else if (btn == "btnClearSchedule") {
        clearScheduledEvents()
    }
}

/* =========================
   Catalog build
   ========================= */

def buildActionCatalog() {
    return [
        hubId: hubId,
        generatedAt: formatNowIso(),
        catalogVersion: 1,
        actionDefinitions: buildActionDefinitions(),
        resources: buildResources()
    ]
}

def buildActionDefinitions() {
    return [
        [
            actionType: "rule",
            label: "Run Hubitat Rule",
            parameters: [
                [
                    name: "targetId",
                    type: "resourceRef",
                    required: true,
                    resourceType: "rule"
                ]
            ]
        ],
        [
            actionType: "speech",
            label: "Speak Text",
            parameters: [
                [
                    name: "text",
                    type: "string",
                    required: true,
                    multiline: true,
                    maxLength: 500
                ],
                [
                    name: "targetId",
                    type: "resourceRef",
                    required: true,
                    resourceType: "speechTarget"
                ]
            ]
        ],
        [
            actionType: "notify",
            label: "Send Notification",
            parameters: [
                [
                    name: "text",
                    type: "string",
                    required: true,
                    multiline: true,
                    maxLength: 500
                ],
                [
                    name: "targetIds",
                    type: "resourceRefList",
                    required: true,
                    resourceType: "notifyDevice"
                ]
            ]
        ]
    ]
}

def buildResources() {
    List resources = []
    resources.addAll(buildRuleActionResources())
    resources.addAll(buildSpeechTargetResources())
    resources.addAll(buildNotifyDeviceResources())
    return resources
}

def buildRuleActionResources() {
    def rules = RMUtils.getRuleList("5.0")
    Map normalized = normalizeRuleList(rules)

    List resources = []

    normalized.each { ruleId, label ->
        if (matchesRuleFilter(label)) {
            resources << [
                resourceId: "rule:${ruleId}",
                type: "rule",
                label: label,
                metadata: [
                    ruleId: ruleId.toInteger()
                ]
            ]
        }
    }

    return resources
}

def buildSpeechTargetResources() {
    List resources = []

    if (allowedSpeechTargets) {
        allowedSpeechTargets.each { dev ->
            resources << [
                resourceId: "speechTarget:${dev.id}",
                type: "speechTarget",
                label: dev.displayName,
                metadata: [
                    deviceId: dev.id.toInteger(),
                    commands: getSupportedCommandNames(dev)
                ]
            ]
        }
    }

    return resources
}

def buildNotifyDeviceResources() {
    List resources = []

    if (allowedNotifyDevices) {
        allowedNotifyDevices.each { dev ->
            resources << [
                resourceId: "notifyDevice:${dev.id}",
                type: "notifyDevice",
                label: dev.displayName,
                metadata: [
                    deviceId: dev.id.toInteger(),
                    commands: getSupportedCommandNames(dev)
                ]
            ]
        }
    }

    return resources
}

Map normalizeRuleList(rules) {
    Map normalized = [:]

    if (rules instanceof List) {
        rules.each { item ->
            if (item instanceof Map) {
                item.each { k, v ->
                    normalized["${k}"] = "${v}"
                }
            }
        }
    } else if (rules instanceof Map) {
        rules.each { k, v ->
            normalized["${k}"] = "${v}"
        }
    }

    return normalized
}

boolean matchesRuleFilter(String label) {
    if (!label || !ruleFilterText) {
        return false
    }

    if (ruleFilterMode == "contains") {
        return label.contains(ruleFilterText)
    }

    // default to startsWith
    return label.startsWith(ruleFilterText)
}

List getSupportedCommandNames(dev) {
    List commandNames = []

    try {
        if (dev.hasCommand("speak")) {
            commandNames << "speak"
        }
    } catch (Exception ignored) {
    }

    try {
        if (dev.hasCommand("deviceNotification")) {
            commandNames << "deviceNotification"
        }
    } catch (Exception ignored) {
    }

    return commandNames
}

/* =========================
   AWS integration
   ========================= */

def pushActionCatalog() {
    def catalog = buildActionCatalog()
    
    if (useMockCatalogPush) {
        state.lastCatalogPushTime = formatNowIso()
        state.lastCatalogPushStatus = "mock"
        log.info "MOCK catalog push payload: ${JsonOutput.prettyPrint(JsonOutput.toJson(catalog))}"
        return
    }
    
    String url = normalizeBaseUrl(awsBaseUrl) + "/hubitat/action-catalog"
    String requestBodyJson = JsonOutput.toJson(catalog)
    state.lastCatalogPushUrl = url
    state.lastCatalogPushRequestBytes = requestBodyJson?.getBytes("UTF-8")?.size() ?: 0
    state.lastCatalogPushError = null

    try {
        def params = [
            uri: url,
            requestContentType: "application/json",
            contentType: "application/json",
            headers: [
                "X-Hubitat-Token": hubitatToken
            ],
            body: catalog,
            timeout: 15
        ]

        httpPost(params) { resp ->
            state.lastCatalogPushTime = formatNowIso()
            state.lastCatalogPushStatus = "HTTP ${resp.status}"
            state.lastCatalogPushResponseBody = summarizeResponseBody(resp?.data)
            log.info "Catalog push response status: ${resp.status}"
            if (resp.status >= 400) {
                log.warn "Catalog push non-200 response body: ${state.lastCatalogPushResponseBody}"
            }
        }

        log.info "Pushed action catalog with ${catalog.resources?.size() ?: 0} resources"
    } catch (Exception e) {
        state.lastCatalogPushTime = formatNowIso()
        state.lastCatalogPushStatus = "error"
        state.lastCatalogPushError = e.message
        log.error "Catalog push failed: ${e.message}"
    }
}

def pullScheduleAndApply() {
    Map schedulePayload = pullSchedule()
    if (!schedulePayload) {
        log.warn "No schedule payload returned"
        return
    }

    applySchedule(schedulePayload)
}

Map pullSchedule() {
    if (useMockSchedulePull) {
        Map mock = buildMockSchedulePayload()
        state.lastSchedulePullTime = formatNowIso()
        state.lastSchedulePullStatus = "mock"
        log.info "Using mock schedule payload: ${JsonOutput.prettyPrint(JsonOutput.toJson(mock))}"
        return mock
    }

    Integer days = scheduleDaysToPull != null ? scheduleDaysToPull as Integer : 7
    String url = normalizeBaseUrl(awsBaseUrl) + "/hubitat/schedule?hubId=${hubId}&days=${days}"
    state.lastSchedulePullUrl = url
    state.lastSchedulePullError = null

    try {
        def params = [
            uri: url,
            contentType: "application/json",
            headers: [
                "X-Hubitat-Token": hubitatToken
            ],
            timeout: 15
        ]

        Map result = null

        httpGet(params) { resp ->
            state.lastSchedulePullTime = formatNowIso()
            state.lastSchedulePullStatus = "HTTP ${resp.status}"
            state.lastSchedulePullResponseBody = summarizeResponseBody(resp?.data)

            if (resp.status == 200) {
                if (resp.data instanceof Map) {
                    result = resp.data
                } else {
                    result = new JsonSlurper().parseText(resp.data.toString())
                }
            } else {
                log.warn "Schedule pull non-200 response body: ${state.lastSchedulePullResponseBody}"
            }
        }

        if (result) {
            state.lastSchedulePullEventCount = result.events?.size() ?: 0
            log.info "Pulled schedule version ${result.scheduleVersion ?: 'unknown'} with ${result.events?.size() ?: 0} events"
        } else {
            state.lastSchedulePullEventCount = 0
        }

        return result
    } catch (Exception e) {
        state.lastSchedulePullTime = formatNowIso()
        state.lastSchedulePullStatus = "error"
        state.lastSchedulePullError = e.message
        log.error "Schedule pull failed: ${e.message}"
        return null
    }
}

String summarizeResponseBody(def body) {
    if (body == null) {
        return "none"
    }

    String raw
    if (body instanceof Map || body instanceof List) {
        raw = JsonOutput.toJson(body)
    } else {
        raw = body.toString()
    }

    Integer maxLength = 500
    if (raw.size() > maxLength) {
        return raw.substring(0, maxLength) + "... (truncated)"
    }

    return raw
}

/* =========================
   Schedule application
   ========================= */

def applySchedule(Map schedulePayload) {
    if (!schedulePayload) {
        log.warn "applySchedule called with null payload"
        return
    }

    clearScheduledEvents()

    state.lastScheduleVersion = schedulePayload.scheduleVersion
    state.pendingEvents = []
    state.resourceIndex = buildResourceIndex(buildActionCatalog().resources)
    initializeBrokenReferenceState()

    List events = schedulePayload.events ?: []

    events.each { event ->
        Map validation = validateScheduleEvent(event)
        if (validation.valid) {
            scheduleEvent(event, schedulePayload.timezone)
        } else {
            log.warn "Skipping invalid event ${event.eventId}: ${validation.message}"
            handleBrokenOrInvalidEvent(event, validation.message)
        }
    }

    log.info "Applied schedule version ${schedulePayload.scheduleVersion}; pending events count=${state.pendingEvents?.size() ?: 0}"
}

Map validateScheduleEvent(Map event) {
    if (!event) {
        return [valid: false, message: "Event is null"]
    }

    if (!event.eventId) {
        return [valid: false, message: "Missing eventId"]
    }

    if (!event.actionType) {
        return [valid: false, message: "Missing actionType"]
    }

    if (!event.date || !event.time) {
        return [valid: false, message: "Missing date or time"]
    }

    if (event.validation && event.validation.status == "broken") {
        return [valid: false, message: "Event marked broken by backend: ${event.validation.message ?: 'unknown'}"]
    }

    Map params = event.parameters ?: [:]
    Map resourceIndex = state.resourceIndex ?: [:]

    if (event.actionType == "rule") {
        String targetId = params.targetId
        if (!targetId) {
            return [valid: false, message: "Rule event missing targetId"]
        }
        if (!resourceIndex[targetId]) {
            return [valid: false, message: "Referenced rule action not found: ${targetId}"]
        }
    } else if (event.actionType == "speech") {
        String targetId = params.targetId
        String text = params.text
        if (!targetId || !text) {
            return [valid: false, message: "Speech event missing targetId or text"]
        }
        if (!resourceIndex[targetId]) {
            return [valid: false, message: "Referenced speech target not found: ${targetId}"]
        }
    } else if (event.actionType == "notify") {
        List targetIds = params.targetIds
        String text = params.text
        if (!targetIds || !text) {
            return [valid: false, message: "Notify event missing targetIds or text"]
        }
        boolean anyMissing = false
        targetIds.each { targetId ->
            if (!resourceIndex[targetId]) {
                anyMissing = true
            }
        }
        if (anyMissing) {
            return [valid: false, message: "One or more notify targets not found"]
        }
    } else {
        return [valid: false, message: "Unsupported actionType ${event.actionType}"]
    }

    return [valid: true]
}

def scheduleEvent(Map event, String timezoneName) {
    Date when = parseScheduleDateTime(event.date, event.time)
    if (!when) {
        handleBrokenOrInvalidEvent(event, "Unable to parse schedule date/time")
        return
    }

    if (when.before(new Date())) {
        log.warn "Skipping past event ${event.eventId} at ${event.date} ${event.time}"
        return
    }

    Map eventData = [
        eventId: event.eventId,
        date: event.date,
        time: event.time,
        actionType: event.actionType,
        parameters: event.parameters ?: [:]
    ]

    state.pendingEvents = (state.pendingEvents ?: []) + [eventData]

    runOnce(when, "executeScheduledEvent", [overwrite: false, data: eventData])

    log.info "Scheduled event ${event.eventId} for ${event.date} ${event.time}"
}

Date parseScheduleDateTime(String dateStr, String timeStr) {
    try {
        String normalizedTime = normalizeTimeString(timeStr)
        return Date.parse("yyyy-MM-dd HH:mm", "${dateStr} ${normalizedTime}", location.timeZone)
    } catch (Exception e) {
        log.error "Failed to parse date/time ${dateStr} ${timeStr}: ${e.message}"
        return null
    }
}

String normalizeTimeString(String timeStr) {
    // Accept HH:mm or H:mm
    if (!timeStr) {
        return timeStr
    }
    return timeStr
}

/* =========================
   Event execution
   ========================= */

def executeScheduledEvent(Map event) {
    log.info "Executing scheduled event: ${event}"

    try {
        if (event.actionType == "rule") {
            executeRuleAction(event)
        } else if (event.actionType == "speech") {
            executeSpeechAction(event)
        } else if (event.actionType == "notify") {
            executeNotifyAction(event)
        } else {
            log.warn "Unsupported action type at execution: ${event.actionType}"
        }
    } catch (Exception e) {
        log.error "Failed to execute event ${event.eventId}: ${e.message}"
    }
}

def executeRuleAction(Map event) {
    String targetId = event.parameters?.targetId
    Integer ruleId = parseNumericResourceId(targetId)

    if (ruleId == null) {
        throw new Exception("Invalid rule targetId ${targetId}")
    }

    def rulesToSend = [ruleId.toString()]
    log.info "Sending rule action to RMUtils: ${rulesToSend}"
    RMUtils.sendAction(rulesToSend, "runRuleAct", app.label, "5.0")
    log.info "Executed rule action ${targetId}"
}

def executeSpeechAction(Map event) {
    String targetId = event.parameters?.targetId
    String text = event.parameters?.text

    Integer deviceId = parseNumericResourceId(targetId)
    def dev = deviceById(deviceId)

    if (!dev) {
        throw new Exception("Speech target not found for ${targetId}")
    }

    if (!text) {
        throw new Exception("Speech text missing")
    }

    dev.speak(text)
    log.info "Executed speech action ${targetId}: ${text}"
}

def executeNotifyAction(Map event) {
    List targetIds = event.parameters?.targetIds ?: []
    String text = event.parameters?.text

    if (!text) {
        throw new Exception("Notify text missing")
    }

    targetIds.each { targetId ->
        Integer deviceId = parseNumericResourceId(targetId)
        def dev = deviceById(deviceId)
        if (dev) {
            dev.deviceNotification(text)
            log.info "Executed notify action ${targetId}: ${text}"
        } else {
            log.warn "Notify target not found for ${targetId}"
        }
    }
}

/* =========================
   Broken references / invalid events
   ========================= */

def initializeBrokenReferenceState() {
    if (state.brokenReferenceKeys == null) {
        state.brokenReferenceKeys = []
    }
}

def handleBrokenOrInvalidEvent(Map event, String message) {
    log.warn "Broken or invalid event ${event?.eventId}: ${message}"

    if (!sendBrokenReferenceNotifications) {
        return
    }

    initializeBrokenReferenceState()

    String key = "event:${event?.eventId}:${message}"
    if (!(state.brokenReferenceKeys as List).contains(key)) {
        state.brokenReferenceKeys = (state.brokenReferenceKeys ?: []) + [key]
        sendBrokenReferenceNotification(event, message)
    }
}

def sendBrokenReferenceNotification(Map event, String message) {
    String text = "Child Scheduler Hub: event ${event?.eventId ?: 'unknown'} is invalid or broken. ${message}"
    log.warn text

    // Optional: fan out to selected notify devices
    if (adminNotifyDevices) {
        adminNotifyDevices.each { dev ->
            try {
                dev.deviceNotification(text)
            } catch (Exception e) {
                log.warn "Failed sending broken reference notification to ${dev.displayName}: ${e.message}"
            }
        }
    }
}

/* =========================
   Utilities
   ========================= */

Map buildMockSchedulePayload() {
    String today = new Date().format("yyyy-MM-dd", location.timeZone)

    String ruleTargetId = findFirstRuleResourceId()
    String speechTargetId = findFirstSpeechTargetResourceId()
    List notifyTargetIds = findNotifyTargetResourceIds()

    if (!findFirstRuleResourceId()) {
        log.warn "No matching rule resources found for mock payload"
    }
    if (!findFirstSpeechTargetResourceId()) {
        log.warn "No speech targets found for mock payload"
    }
    if (!findNotifyTargetResourceIds()) {
        log.warn "No notify targets found for mock payload"
    }    
    
    return [
        hubId: hubId,
        generatedAt: formatNowIso(),
        scheduleVersion: 1,
        timezone: location.timeZone?.ID ?: "America/New_York",
        events: [
            [
                eventId: "mock-rule-1",
                date: today,
                time: timeStringMinutesFromNow(1),
                actionType: "rule",
                parameters: [
                    targetId: ruleTargetId
                ]
            ],
            [
                eventId: "mock-speech-1",
                date: today,
                time: timeStringMinutesFromNow(2),
                actionType: "speech",
                parameters: [
                    targetId: speechTargetId,
                    text: "This is a mock speech test from Child Scheduler Hub."
                ]
            ],
            [
                eventId: "mock-notify-1",
                date: today,
                time: timeStringMinutesFromNow(3),
                actionType: "notify",
                parameters: [
                    targetIds: notifyTargetIds,
                    text: "This is a mock notify test from Child Scheduler Hub."
                ]
            ],
            [
                eventId: "mock-broken-1",
                date: today,
                time: timeStringMinutesFromNow(4),
                actionType: "rule",
                parameters: [
                    targetId: "rule:999999"
                ],
                validation: [
                    status: "broken",
                    message: "Mock broken reference",
                    originalLabel: "ZCSA Missing Rule"
                ]
            ]
        ]
    ]
}

String findFirstRuleResourceId() {
    def match = buildRuleActionResources()?.find { true }
    return match?.resourceId
}

String findFirstSpeechTargetResourceId() {
    def match = buildSpeechTargetResources()?.find { true }
    return match?.resourceId
}

List findNotifyTargetResourceIds() {
    return buildNotifyDeviceResources().collect { it.resourceId }
}

String timeStringMinutesFromNow(Integer minutesFromNow) {
    Date when = new Date(now() + (minutesFromNow * 60 * 1000L))
    return when.format("HH:mm", location.timeZone)
}

Map buildResourceIndex(List resources) {
    Map idx = [:]
    resources.each { resource ->
        idx[resource.resourceId] = resource
    }
    return idx
}

Integer parseNumericResourceId(String resourceId) {
    if (!resourceId) {
        return null
    }

    List parts = resourceId.tokenize(":")
    if (parts.size() != 2) {
        return null
    }

    try {
        return parts[1].toInteger()
    } catch (Exception e) {
        return null
    }
}

def deviceById(Integer deviceId) {
    if (deviceId == null) {
        return null
    }

    if (allowedSpeechTargets) {
        def match = allowedSpeechTargets.find { it.id.toInteger() == deviceId }
        if (match) {
            return match
        }
    }

    if (allowedNotifyDevices) {
        def match = allowedNotifyDevices.find { it.id.toInteger() == deviceId }
        if (match) {
            return match
        }
    }

    return null
}

def clearScheduledEvents() {
    unschedule()
    state.pendingEvents = []
    log.info "Cleared scheduled events"
}

String normalizeBaseUrl(String base) {
    if (!base) {
        return ""
    }
    if (base.endsWith("/")) {
        return base[0..-2]
    }
    return base
}

String formatNowIso() {
    return new Date().format("yyyy-MM-dd'T'HH:mm:ssZ", location.timeZone)
}
