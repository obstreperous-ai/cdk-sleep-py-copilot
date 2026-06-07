# Architecture — Event-Driven Sleep Audio Pipeline

> **Status:** **Complete pipeline wiring with input validation implemented (Issue #8)**. All components 
> are now integrated end-to-end: Input/Output S3 buckets, EventBridge rule, Step Functions state machine 
> with validation, Lambda processor with input validation, Polly integration, DynamoDB metadata table, 
> SNS topics for notifications, and comprehensive error handling. State machine workflow: 
> S3 upload → EventBridge → DynamoDB write → Lambda (validation) → Polly → Status update → Notification.
> Lambda function now includes robust input validation (required fields, file extensions).
> This document is the **single source of truth** for the system design. All future issues
> and pull requests must keep their implementation consistent with this file and update it
> when the design evolves.
> 
> **Implementation Progress:**
> - ✅ Issue #2: Design baseline established
> - ✅ Issue #3: Core S3 Buckets + EventBridge Rule (completed)
> - ✅ Issue #4: Step Functions State Machine Skeleton + Polly Integration (completed)
> - ✅ Issue #5: DynamoDB Metadata Table + State Machine Input/Output Handling (completed)
> - ✅ Issue #6: SNS Notifications + Basic Error Handling &amp; Status Updates (completed)
> - ✅ Issue #7: Basic Lambda Function Skeleton + Integration with State Machine (completed)
> - ✅ Issue #8: TDD: Complete Pipeline Wiring, Input Validation &amp; Basic End-to-End Flow (completed)
> - 🔜 Issue #9: TDD: Pipeline Testing, Refinement &amp; Deployment Preparation (next)

---

## 1. High-Level Overview

The **Event-Driven Sleep Audio Pipeline** is a serverless, fully event-driven
system on AWS that ingests raw audio uploaded by users (voice recordings,
ambient sounds), processes and enriches it into soothing sleep audio, and
publishes the processed result together with rich metadata and notifications.

The pipeline is designed around three principles:

1. **Event-driven & serverless** — every stage is triggered by an event rather
   than by polling or long-running servers. This keeps the system cheap at idle,
   elastic under load, and operationally simple.
2. **Decoupled & observable** — stages communicate through S3, EventBridge, and
   SNS so that each component can evolve, fail, and retry independently, with
   full visibility through CloudWatch.
3. **Secure by default** — least-privilege IAM, encryption at rest and in
   transit, and fully private buckets are baseline requirements, not add-ons.

The infrastructure is defined with the **AWS CDK (Python)** and supports
**multiple environments** (`dev` / `stage` / `prod`) selected through CDK
context, so the same code base produces isolated, independently configured
stacks per environment.

---

## 2. Data Flow

The end-to-end flow of a single audio file through the pipeline:

1. **Upload** — A user (via an application or direct pre-signed URL) uploads a
   raw audio file to the **Input S3 bucket** under a key that encodes the
   `user_id` (for example `raw/{user_id}/{recording_id}.wav`).
2. **Event detection** — S3 emits an **Object Created** event. An **EventBridge**
   rule matches uploads to the input bucket (filtered by prefix/suffix) and
   triggers the processing workflow.
3. **Orchestration** — EventBridge starts an **AWS Step Functions** state
   machine, passing the bucket name and object key as input. Step Functions
   orchestrates the multi-step processing with built-in retries, error
   handling, and per-step observability.
4. **Validation & metadata extraction** — The first task validates the object
   (size limits, allowed content types, decodable audio) and extracts metadata
   such as duration, format, sample rate, and the `user_id` derived from the key.
   An initial record is written to **DynamoDB** with `processing_status =
   PROCESSING`.
5. **Audio generation / enhancement** — The workflow enriches the audio:
   - **Amazon Polly** synthesizes soothing narration / text-to-speech (for
     example guided sleep prompts or calming voice overlays).
   - **Amazon Bedrock** (optional) generates AI sleep soundscapes or enhances
     the audio. This branch is optional and can be skipped via context/feature
     flag so early environments incur no Bedrock cost.
6. **Persist output** — The processed file is written to the **Output S3 bucket**
   (with **versioning enabled**) under a structured key such as
   `processed/{user_id}/{recording_id}.mp3`.
7. **Record results** — The DynamoDB item is updated with the final
   `processing_status` (`COMPLETED` or `FAILED`), output location, duration, and
   timestamps.
8. **Notify** — Step Functions publishes a message to an **SNS topic** on
   completion or failure. Subscribers (email, downstream services, or a future
   notification Lambda) are decoupled from the pipeline.
9. **Observe** — Every step emits **CloudWatch Logs** and metrics. **CloudWatch
   Alarms** watch for Step Functions execution failures and a DLQ/error
   condition, alerting operators via SNS.

> **Consistency note:** The numbered flow above maps one-to-one onto the Mermaid
> diagram in Section 4 and the service table in Section 3.

---

## 3. Key AWS Services and Rationale

| Stage | Service | Why this service |
| --- | --- | --- |
| Ingestion | **Amazon S3** (Input bucket) | Durable, cheap object storage; native event notifications; supports pre-signed uploads and lifecycle rules. Private with encryption at rest. |
| Event routing | **Amazon EventBridge** | Decouples upload from processing; declarative content-based rules; easy to add new targets later without touching producers. |
| Orchestration | **AWS Step Functions** | Visual, auditable multi-step workflow with native retries, catch/error handling, timeouts, and per-step CloudWatch integration. Preferred over a single monolithic Lambda for clarity and resilience. |
| Compute (tasks) | **AWS Lambda** | Short-lived, stateless functions for validation, metadata extraction, and service orchestration. Pay-per-use and auto-scaling. |
| Voice synthesis | **Amazon Polly** | Managed, high-quality text-to-speech for soothing narration; neural voices; no model hosting required. |
| AI audio (optional) | **Amazon Bedrock** | Managed foundation-model access for AI-generated soundscapes / enhancement without managing GPUs. Feature-flagged to control cost. |
| Output storage | **Amazon S3** (Output bucket, versioned) | Durable storage of processed artifacts; **versioning** protects against overwrites and enables rollback/audit. |
| Metadata | **Amazon DynamoDB** | Serverless, low-latency key-value store for per-recording metadata and status; scales to zero cost at idle; natural fit for `user_id` / `recording_id` access patterns. |
| Notifications | **Amazon SNS** | Fan-out completion/error events to multiple decoupled subscribers (email, Lambda, queues). |
| Observability | **Amazon CloudWatch** (Logs, Metrics, Alarms) | Centralized logging, metrics, and alarming across all stages. |
| Security | **AWS IAM** + **AWS KMS** | Least-privilege roles per component and encryption key management. |

---

## 4. Architecture Diagram

**Legend:**
- ✅ = Implemented (Issue #3-8)
- 🔜 = Planned (Issue #9+)

```mermaid
flowchart TD
    user([User / Client App])

    subgraph ingestion["✅ Ingestion (Implemented)"]
        input[("✅ Input S3 Bucket\nSleepAudioInputBucket\nprivate · encrypted · versioned")]
        eb{{"✅ EventBridge Rule\nSleepAudioProcessingRule\nObject Created"}}
    end

    subgraph processing["✅ Complete Processing Pipeline — AWS Step Functions"]
        sfn["✅ Step Functions\nSleepAudioPipelineStateMachine"]
        write_metadata["✅ Write Initial Metadata\nDynamoDB PutItem\nstatus=PROCESSING"]
        audio_processor["✅ Audio Processor Lambda\nSleepAudioProcessor\n✅ Input Validation"]
        validate_result{"✅ Validation Check\n(in Lambda)"}
        polly["✅ Amazon Polly Task\nSynthesizeSpeech (skeleton)"]
        update_completed["✅ Update Status COMPLETED\nDynamoDB UpdateItem"]
        update_failed["✅ Update Status FAILED\nDynamoDB UpdateItem"]
        bedrock["🔜 Amazon Bedrock\nAI Soundscapes (optional)"]
        persist["🔜 Persist Processed Audio\n(Lambda)"]
    end

    subgraph storage["Storage &amp; State"]
        output[("✅ Output S3 Bucket\nSleepAudioOutputBucket\nprivate · encrypted · versioned")]
        ddb[("✅ DynamoDB\nSleepAudioMetadataTable\naudioId · status · metadata")]
    end

    subgraph notify_obs["✅ Notifications &amp; Observability"]
        sns_success(["✅ SNS Topic\nSleepAudioPipelineCompleted"])
        sns_failed(["✅ SNS Topic\nSleepAudioPipelineFailed"])
        cw["✅ CloudWatch Logs\nStep Functions + Lambda logging"]
    end

    user -->|1. upload raw audio| input
    input -->|2. Object Created event| eb
    eb -->|3. start execution| sfn
    sfn -->|4a. write initial record| write_metadata
    write_metadata -->|status=PROCESSING| ddb
    write_metadata -->|on error| update_failed
    write_metadata -->|4b. invoke with validation| audio_processor
    audio_processor -->|validate input| validate_result
    validate_result -->|✅ validation passed| polly
    validate_result -->|❌ validation failed| update_failed
    audio_processor -->|on exception| update_failed
    polly -->|on success| update_completed
    polly -->|on error| update_failed
    update_completed -->|status=COMPLETED| ddb
    update_completed --> sns_success
    update_failed -->|status=FAILED + error| ddb
    update_failed --> sns_failed
    sns_success -->|notify subscribers| user
    sns_failed -->|notify subscribers| user
    sfn -.->|CloudWatch Logs| cw
    audio_processor -.->|CloudWatch Logs| cw
    
    polly -.->|5. (future) pass to enhance| bedrock
    bedrock -.-> persist
    persist -.->|6. write processed file| output
    
    bedrock -.->|logs &amp; metrics| cw
    persist -.->|logs &amp; metrics| cw
    cw -.->|7. alarm on failure| sns_failed
    
    style input fill:#90EE90
    style output fill:#90EE90
    style eb fill:#90EE90
    style sfn fill:#90EE90
    style audio_processor fill:#90EE90
    style validate_result fill:#FFD700
    style polly fill:#90EE90
    style cw fill:#90EE90
    style ddb fill:#90EE90
    style write_metadata fill:#90EE90
    style update_completed fill:#90EE90
    style update_failed fill:#FF6B6B
    style sns_success fill:#90EE90
    style sns_failed fill:#FF6B6B
```

**Current Implementation (Issue #3-8):**
- ✅ Input and Output S3 buckets are created with encryption, versioning, and public access blocking
- ✅ EventBridge rule is configured to trigger on S3 Object Created events
- ✅ Step Functions state machine is the target of the EventBridge rule
- ✅ Step Functions state machine includes a DynamoDB PutItem task to write initial metadata
- ✅ DynamoDB table (SleepAudioMetadataTable) stores processing metadata and status
- ✅ State machine captures S3 event data (bucket, key) and writes to DynamoDB with status=PROCESSING
- ✅ Lambda function (SleepAudioProcessor) with complete input validation
- ✅ Lambda validates: required fields (detail, bucket, key), file extensions (mp3, wav, m4a, ogg, flac)
- ✅ Lambda positioned in workflow: metadata write → Lambda (validation) → Polly → status update
- ✅ Lambda has read-only DynamoDB access and CloudWatch Logs permissions
- ✅ State machine can invoke Lambda with proper IAM permissions
- ✅ Error handling includes Lambda task with catch blocks routing to failure path
- ✅ Step Functions state machine includes a skeleton Polly task using CallAwsService
- ✅ CloudWatch Logs enabled for Step Functions with full execution data logging
- ✅ SNS topics created for success and failure notifications with encryption
- ✅ State machine includes error handling with Catch blocks for all tasks
- ✅ DynamoDB status updates for COMPLETED and FAILED states
- ✅ SNS publish tasks for success and failure notifications
- ✅ Complete end-to-end validation flow with clear error paths

---

## 5. End-to-End Flow Details

### Success Path (Happy Path)

1. **Upload Trigger**
   - User/application uploads an audio file (e.g., `recording.mp3`) to the Input S3 bucket
   - S3 emits an **Object Created** event to EventBridge

2. **Event Routing**
   - EventBridge rule matches the S3 event pattern
   - EventBridge starts a new Step Functions execution, passing the full S3 event as input

3. **Initial Metadata Write**
   - Step Functions executes **WriteInitialMetadata** task
   - DynamoDB PutItem creates a record with:
     - `audioId`: S3 object key
     - `status`: "PROCESSING"
     - `inputBucket`: S3 bucket name
     - `inputKey`: S3 object key
     - `createdAt`, `updatedAt`: Execution timestamps

4. **Input Validation (Lambda)**
   - Step Functions invokes **SleepAudioProcessor** Lambda
   - Lambda validates:
     - ✅ Required field: `detail` exists in event
     - ✅ Required field: `bucket.name` is present and non-empty
     - ✅ Required field: `object.key` is present and non-empty
     - ✅ File extension: Must be one of `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`
   - If validation passes: Lambda returns `{status: 'success', ...}`
   - If validation fails: Lambda returns `{status: 'error', errorType: 'ValidationError', ...}`

5. **Audio Processing (Polly)**
   - Step Functions executes **InvokePolly** task (skeleton implementation)
   - Calls Amazon Polly's SynthesizeSpeech API
   - Returns audio synthesis result (placeholder for future enhancement)

6. **Status Update (Success)**
   - Step Functions executes **UpdateStatusCompleted** task
   - DynamoDB UpdateItem sets:
     - `status`: "COMPLETED"
     - `updatedAt`: Current timestamp

7. **Success Notification**
   - Step Functions executes **PublishSuccessNotification** task
   - Publishes message to **SleepAudioPipelineCompleted** SNS topic
   - Message includes: audioId, executionId, timestamp, status

### Failure Path (Error Handling)

At any point in the workflow, if an error occurs:

1. **Error Catch**
   - Each task has a `Catch` block configured for `States.ALL` errors
   - Error details are captured in `$.error` field (preserves original event)

2. **Status Update (Failure)**
   - Workflow routes to **UpdateStatusFailed** task
   - DynamoDB UpdateItem sets:
     - `status`: "FAILED"
     - `errorInfo`: Error message from `$.error`
     - `updatedAt`: Current timestamp

3. **Failure Notification**
   - Step Functions executes **PublishFailureNotification** task
   - Publishes message to **SleepAudioPipelineFailed** SNS topic
   - Message includes: audioId, executionId, timestamp, error details

### Validation Error Scenarios

**Lambda Input Validation Errors:**

| Error Case | Detected By | Error Message | Status |
|-----------|-------------|---------------|--------|
| Missing `detail` field | Lambda | "Missing required 'detail' field in event" | FAILED |
| Missing bucket name | Lambda | "Missing or empty bucket name in event" | FAILED |
| Empty bucket name | Lambda | "Missing or empty bucket name in event" | FAILED |
| Missing object key | Lambda | "Missing or empty object key in event" | FAILED |
| Empty object key | Lambda | "Missing or empty object key in event" | FAILED |
| Unsupported file format | Lambda | "Unsupported audio format '.ext'. Supported formats: ..." | FAILED |

All validation errors:
- Return `{status: 'error', errorType: 'ValidationError'}`
- Are logged to CloudWatch
- Trigger the failure path in Step Functions
- Result in DynamoDB status = "FAILED"
- Trigger SNS failure notification

---

## 6. Security

- **Private buckets** — Both S3 buckets block all public access; uploads use
  pre-signed URLs and downloads are mediated by the application.
- **Encryption at rest** — S3 buckets, DynamoDB, and SNS use encryption at rest
  (SSE-S3/KMS, DynamoDB encryption, SNS encryption). KMS keys are scoped per
  environment.
- **Encryption in transit** — TLS is enforced; bucket policies deny
  non-HTTPS (`aws:SecureTransport = false`) requests.
- **Least-privilege IAM** — Each Lambda and the Step Functions role receives a
  dedicated role granting only the specific actions and resources it needs
  (for example, the validation function may read the input bucket but not write
  the output bucket). No wildcard `*` resource grants in production.
- **Bucket separation** — Input and output buckets are isolated so that raw
  user content and processed artifacts have independent policies and lifecycles.
- **Data retention** — Lifecycle rules expire raw uploads after processing;
  output versioning retains processed artifacts for audit/rollback.

---

## 7. Observability

- **Structured logging** — Every Lambda and Step Functions execution logs to
  CloudWatch Logs with retention configured per environment.
- **Metrics** — Step Functions execution success/failure counts, Lambda errors
  and durations, and DynamoDB throttles are tracked.
- **Alarms** — Baseline CloudWatch Alarms on Step Functions `ExecutionsFailed`
  and a processing error/DLQ condition notify operators through the SNS topic.
- **Traceability** — Each recording's lifecycle is reconstructable from its
  DynamoDB item (`processing_status`, timestamps) and correlated Step Functions
  execution ID.

---

## 8. Cost Considerations

- **Serverless / pay-per-use** — S3, Lambda, Step Functions, DynamoDB (on-demand),
  SNS, and EventBridge cost effectively nothing at idle; the system scales with
  actual usage.
- **Optional Bedrock** — The most expensive component (Bedrock) is feature-flagged
  via CDK context so non-production environments avoid foundation-model charges.
- **Lifecycle rules** — Expiring raw inputs and transitioning infrequently
  accessed output versions to cheaper storage classes controls long-term S3 cost.
- **Right-sized environments** — `dev`/`stage` can use shorter log retention and
  smaller alarms thresholds than `prod`.

---

## 9. Multi-Environment Support

Environments (`dev` / `stage` / `prod`) are selected through **CDK context**
(for example `cdk deploy -c env=dev`). The environment name drives:

- Resource naming / removal policies (e.g. `RETAIN` in prod, `DESTROY` in dev).
- Feature flags such as enabling the optional Bedrock branch.
- Log retention, alarm thresholds, and KMS key configuration.

Each environment synthesizes an isolated stack so changes can be promoted
`dev → stage → prod` safely.

---

## 10. Future Extensibility

- **New processing steps** — Additional Step Functions tasks (transcription,
  loudness normalization, format conversion) slot in without changing producers.
- **Additional event sources** — EventBridge can route new event types (scheduled
  jobs, API-driven requests) to the same workflow.
- **More notification channels** — New SNS subscribers (mobile push, queues,
  webhooks) attach without modifying the pipeline.
- **Search / analytics** — DynamoDB Streams can feed downstream indexing or
  analytics for processed-audio discovery.
- **API layer** — A future API Gateway + Lambda front end can issue pre-signed
  upload URLs and expose processing status from DynamoDB.

---

## 11. Implementation Status

### Issue #3: Core S3 Buckets + EventBridge Rule (✅ Completed)

**Implemented Resources:**

1. **SleepAudioInputBucket** (Input S3 Bucket)
   - Encryption: S3-managed (SSE-S3)
   - Versioning: Enabled
   - Public Access: Fully blocked (BLOCK_ALL)
   - EventBridge: Enabled for Object Created notifications
   - Removal Policy: DESTROY (dev/test) — should be RETAIN in production
   - Auto-delete objects: Enabled (dev/test) — should be disabled in production

2. **SleepAudioOutputBucket** (Output S3 Bucket)
   - Encryption: S3-managed (SSE-S3)
   - Versioning: Enabled
   - Public Access: Fully blocked (BLOCK_ALL)
   - Removal Policy: DESTROY (dev/test) — should be RETAIN in production
   - Auto-delete objects: Enabled (dev/test) — should be disabled in production

3. **SleepAudioProcessingRule** (EventBridge Rule)
   - Event Pattern: Triggers on `Object Created` events from Input Bucket
   - State: ENABLED
   - Target: CloudWatch Logs (placeholder — will be replaced with Step Functions in Issue #4)
   - Description: "Triggers processing workflow when audio is uploaded to input bucket"

**Security Features:**
- Both buckets use S3-managed encryption (SSE-S3) by default
- Both buckets block all public access via `PublicAccessBlockConfiguration`
- Input bucket has EventBridge notifications enabled for event-driven processing
- IAM roles follow least-privilege principles (managed by CDK)

**Test Coverage:**
- ✅ Input bucket encryption verification
- ✅ Input bucket versioning verification
- ✅ Input bucket public access blocking verification
- ✅ Output bucket existence and count verification
- ✅ EventBridge rule event pattern verification
- ✅ EventBridge rule target configuration verification

---

### Issue #4: Step Functions State Machine Skeleton + Polly Integration (✅ Completed)

**Implemented Resources:**

1. **SleepAudioPipelineStateMachine** (Step Functions State Machine)
   - Definition: Single-state skeleton with Polly integration using `CallAwsService`
   - Task: InvokePolly — calls Amazon Polly's `synthesizeSpeech` API
   - Parameters: Placeholder text, VoiceId (Joanna), OutputFormat (mp3), Engine (neural)
   - CloudWatch Logging: ALL level with execution data included
   - Tracing: AWS X-Ray tracing enabled
   - Execution Role: Auto-generated with least-privilege permissions (Polly:SynthesizeSpeech)

2. **StateMachineLogGroup** (CloudWatch Log Group)
   - Purpose: Centralized logging for Step Functions executions
   - Removal Policy: DESTROY (dev/test)
   - Log Level: ALL with execution data

3. **EventBridge Rule Target Update**
   - Previous: CloudWatch Logs (placeholder)
   - Current: Step Functions state machine
   - Input: Full event payload passed from S3 Object Created event
   - Role: Auto-generated IAM role for EventBridge to invoke Step Functions

**Security Features:**
- State machine execution role follows least-privilege principles (only Polly actions)
- EventBridge has dedicated IAM role to start executions
- All permissions are scoped to specific resources where possible
- CloudWatch logging enables full audit trail of executions

**Test Coverage:**
- ✅ Step Functions state machine resource exists
- ✅ State machine has CloudWatch logging enabled with execution data
- ✅ State machine definition contains expected properties
- ✅ EventBridge rule targets Step Functions (not CloudWatch Logs)
- ✅ State machine has proper execution IAM role

**Architecture Updates:**
- ✅ Mermaid diagram updated to show Step Functions orchestration layer
- ✅ EventBridge → Step Functions integration shown
- ✅ Polly task highlighted as implemented skeleton
- ✅ CloudWatch Logs role clarified (Step Functions logging, not EventBridge target)

**Next Steps (Issue #5):**
- Add DynamoDB table for metadata and processing status
- Implement input/output transformation in state machine
- Add validation Lambda function

---

### Issue #5: DynamoDB Metadata Table + State Machine Input/Output Handling (✅ Completed)

**Implemented Resources:**

1. **SleepAudioMetadataTable** (DynamoDB Table)
   - Partition Key: `audioId` (String) — derived from S3 object key
   - Billing Mode: PAY_PER_REQUEST (on-demand) for dev/test
   - Encryption: AWS-managed (SSE-DynamoDB)
   - Point-in-Time Recovery: Enabled for data protection
   - Removal Policy: DESTROY (dev/test) — should be RETAIN in production

2. **WriteInitialMetadata Task** (Step Functions DynamoDB PutItem)
   - First task in state machine workflow
   - Captures S3 event data from EventBridge input:
     - `audioId`: Object key from `$.detail.object.key`
     - `inputBucket`: Bucket name from `$.detail.bucket.name`
     - `inputKey`: Object key from `$.detail.object.key`
     - `status`: Initial value set to "PROCESSING"
     - `createdAt`: Execution start time from `$$.Execution.StartTime`
     - `updatedAt`: Execution start time from `$$.Execution.StartTime`
   - Result stored in `$.metadata` path for downstream tasks

3. **State Machine Chain Update**
   - Previous: Single Polly task
   - Current: DynamoDB PutItem → Polly task
   - Flow: S3 event → Write metadata → Invoke Polly (skeleton)
   - State machine role automatically granted `dynamodb:PutItem` permission

**Metadata Schema:**

| Attribute | Type | Description |
| --- | --- | --- |
| `audioId` | String (PK) | S3 object key, uniquely identifies the audio processing job |
| `status` | String | Current processing status: PROCESSING, COMPLETED, FAILED |
| `inputBucket` | String | Source S3 bucket name |
| `inputKey` | String | Source S3 object key |
| `createdAt` | String (ISO 8601) | State machine execution start timestamp |
| `updatedAt` | String (ISO 8601) | Last update timestamp |

*Note: Future attributes (e.g., `outputBucket`, `outputKey`, `duration`, `errorMessage`) will be added in subsequent issues.*

**Security Features:**
- DynamoDB table uses AWS-managed encryption (SSE-DynamoDB)
- Point-in-time recovery enabled for data protection and backup
- State machine execution role follows least-privilege principles (only `dynamodb:PutItem` on specific table)
- All permissions are scoped to specific resources via CDK-generated policies

**Test Coverage:**
- ✅ DynamoDB table resource existence verification
- ✅ Table partition key schema (audioId) verification
- ✅ Table encryption enabled verification
- ✅ On-demand billing mode verification
- ✅ Point-in-time recovery enabled verification
- ✅ State machine definition includes DynamoDB task verification
- ✅ State machine role has DynamoDB permissions verification
- ✅ State machine chain includes multiple tasks verification

**Architecture Updates:**
- ✅ Mermaid diagram updated to show DynamoDB table and write_metadata task
- ✅ State machine flow updated: EventBridge → DynamoDB write → Polly
- ✅ DynamoDB table highlighted as implemented with metadata schema
- ✅ Metadata attributes documented in implementation section

**Input/Output Handling:**
- ✅ S3 event data (bucket name, object key) mapped into state machine input
- ✅ EventBridge passes full event payload using `RuleTargetInput.from_event_path("$")`
- ✅ State machine uses JsonPath expressions to extract fields from event
- ✅ DynamoDB PutItem captures event context and execution metadata

**Next Steps (Issue #6):**
- Add SNS topic for completion/error notifications
- Implement basic error handling in state machine (Catch/Retry)
- Update DynamoDB status on completion/failure
- Add CloudWatch alarms for Step Functions execution failures

---

### Issue #6: SNS Notifications + Basic Error Handling &amp; Status Updates (✅ Completed)

**Implemented Resources:**

1. **SnsEncryptionKey** (KMS Key for SNS Encryption)
   - Description: KMS key for SNS topic encryption
   - Key Rotation: Enabled for security best practices
   - Removal Policy: DESTROY (dev/test) — should be RETAIN in production

2. **SleepAudioPipelineCompleted** (SNS Topic)
   - Display Name: "Sleep Audio Pipeline Completed"
   - Encryption: KMS-managed encryption using dedicated key
   - Purpose: Notifies subscribers when pipeline processing completes successfully

3. **SleepAudioPipelineFailed** (SNS Topic)
   - Display Name: "Sleep Audio Pipeline Failed"
   - Encryption: KMS-managed encryption using dedicated key
   - Purpose: Notifies subscribers when pipeline processing fails

4. **UpdateStatusCompleted Task** (Step Functions DynamoDB UpdateItem)
   - Updates DynamoDB record on successful processing
   - Sets `status` to "COMPLETED"
   - Updates `updatedAt` timestamp
   - Uses UpdateExpression for efficient partial updates
   - Result stored in `$.statusUpdate` path

5. **PublishSuccessNotification Task** (Step Functions SNS Publish)
   - Publishes success notification to completed topic
   - Message includes: status, audioId, executionId, timestamp
   - Subject: "Sleep Audio Pipeline - Processing Completed"
   - Result stored in `$.notification` path

6. **UpdateStatusFailed Task** (Step Functions DynamoDB UpdateItem)
   - Updates DynamoDB record on processing failure
   - Sets `status` to "FAILED"
   - Updates `updatedAt` timestamp
   - Captures error information in `errorInfo` attribute
   - Result stored in `$.statusUpdate` path

7. **PublishFailureNotification Task** (Step Functions SNS Publish)
   - Publishes failure notification to failed topic
   - Message includes: status, audioId, executionId, timestamp, error
   - Subject: "Sleep Audio Pipeline - Processing Failed"
   - Result stored in `$.notification` path

8. **Error Handling Implementation**
   - Catch blocks added to all tasks in the workflow
   - Errors caught: "States.ALL" (catches any error type)
   - Error path: Routes to failure chain (UpdateStatusFailed → PublishFailureNotification)
   - Error details captured in `$.error` path for debugging

**State Machine Flow (Updated):**

```
Success Path:
WriteInitialMetadata → InvokePolly → UpdateStatusCompleted → PublishSuccessNotification

Failure Path (from any task):
[Task Error] → UpdateStatusFailed → PublishFailureNotification
```

**Metadata Schema (Updated):**

| Attribute | Type | Description |
| --- | --- | --- |
| `audioId` | String (PK) | S3 object key, uniquely identifies the audio processing job |
| `status` | String | Current processing status: PROCESSING, COMPLETED, FAILED |
| `inputBucket` | String | Source S3 bucket name |
| `inputKey` | String | Source S3 object key |
| `createdAt` | String (ISO 8601) | State machine execution start timestamp |
| `updatedAt` | String (ISO 8601) | Last update timestamp |
| `errorInfo` | String (optional) | Error details when status is FAILED |

*Note: Future attributes (e.g., `outputBucket`, `outputKey`, `duration`) will be added in subsequent issues.*

**Security Features:**
- SNS topics use KMS encryption with dedicated encryption key
- KMS key rotation enabled for enhanced security
- State machine execution role follows least-privilege principles:
  - `sns:Publish` permission scoped to specific SNS topics
  - `dynamodb:PutItem` and `dynamodb:UpdateItem` scoped to specific table
- All IAM policies auto-generated by CDK with resource-level restrictions
- No wildcard permissions granted

**Test Coverage:**
- ✅ SNS topics existence verification (2 topics)
- ✅ SNS topics encryption enabled verification
- ✅ State machine role has SNS publish permissions verification
- ✅ State machine role has DynamoDB update permissions verification
- ✅ State machine definition includes error handling verification
- ✅ State machine has SNS publish tasks verification
- ✅ State machine has status update tasks verification

**Architecture Updates:**
- ✅ Mermaid diagram updated to show SNS topics and notification flows
- ✅ Error handling paths visualized in diagram (success and failure paths)
- ✅ DynamoDB status update tasks shown for both COMPLETED and FAILED states
- ✅ SNS topics highlighted as implemented with encryption
- ✅ Notification layer documented in implementation section

**Notification Message Structure:**

Success Notification:
```json
{
  "status": "COMPLETED",
  "audioId": "<S3 object key>",
  "executionId": "<Step Functions execution ID>",
  "timestamp": "<ISO 8601 timestamp>"
}
```

Failure Notification:
```json
{
  "status": "FAILED",
  "audioId": "<S3 object key>",
  "executionId": "<Step Functions execution ID>",
  "timestamp": "<ISO 8601 timestamp>",
  "error": "<error details>"
}
```

**Next Steps (Issue #7):**
- Add Lambda function for audio validation
- Integrate validation Lambda with state machine
- Implement audio file size and format validation
- Add audio metadata extraction (duration, format, sample rate)

---

### Issue #7: Basic Lambda Function Skeleton + Integration with State Machine (✅ Completed)

**Implemented Resources:**

1. **SleepAudioProcessor** (AWS Lambda Function)
   - Runtime: Python 3.12
   - Handler: `audio_processor.handler`
   - Code: `lambda/audio_processor.py`
   - Purpose: Minimal skeleton for future audio processing, validation, and metadata enrichment
   - Environment Variables:
     - `METADATA_TABLE_NAME`: Reference to DynamoDB metadata table
   - Execution Role: Auto-generated with least-privilege permissions
   - Timeout: Default (3 seconds) — sufficient for skeleton
   - Description: "Processes audio files - validates, extracts metadata, and enriches data"

2. **Lambda Handler Functionality** (Skeleton Implementation)
   - Receives event from Step Functions state machine
   - Extracts S3 event details (bucket name, object key)
   - Logs input for debugging and observability
   - Returns success response with audioId and processing metadata
   - Includes basic error handling with try-catch
   - **Future Enhancements Planned:**
     - Audio file validation (format, size, duration)
     - Metadata extraction (codec, sample rate, duration)
     - S3 object tagging or categorization
     - DynamoDB metadata enrichment

3. **InvokeAudioProcessor Task** (Step Functions LambdaInvoke)
   - Added to state machine workflow after `WriteInitialMetadata`
   - Positioned before `InvokePolly` task
   - Input Payload:
     - `detail`: S3 event details from `$.detail`
     - `metadata`: Initial metadata from `$.metadata`
   - Output Path: Full event state preserved
   - Result Path: `$.processorResult` — Lambda response stored here
   - Error Handling: Catch block routes errors to failure path

4. **IAM Permissions (Least-Privilege)**
   - **Lambda Execution Role:**
     - `AWSLambdaBasicExecutionRole` managed policy (CloudWatch Logs)
     - `dynamodb:GetItem` on metadata table (read-only for future use)
     - `dynamodb:Query` on metadata table (read-only for future use)
   - **State Machine Execution Role:**
     - `lambda:InvokeFunction` on SleepAudioProcessor function

**State Machine Flow (Updated):**

```
Success Path:
WriteInitialMetadata → InvokeAudioProcessor → InvokePolly → UpdateStatusCompleted → PublishSuccessNotification

Failure Path (from any task):
[Task Error] → UpdateStatusFailed → PublishFailureNotification
```

**Lambda Response Format:**

Success Response:
```json
{
  "status": "success",
  "message": "Audio processor invoked successfully",
  "audioId": "<S3 object key>",
  "bucket": "<S3 bucket name>",
  "processorFunction": "<Lambda function name>",
  "requestId": "<Lambda request ID>"
}
```

Error Response:
```json
{
  "status": "error",
  "message": "Error processing audio: <error details>",
  "errorType": "<exception type>"
}
```

**Security Features:**
- Lambda execution role follows least-privilege principles:
  - Read-only DynamoDB access (GetItem, Query) scoped to metadata table
  - CloudWatch Logs access via managed policy
  - No write access to DynamoDB (state machine handles status updates)
  - No S3 access in skeleton (to be added when needed)
- State machine role granted Lambda invoke permission scoped to specific function
- All IAM policies auto-generated by CDK with resource-level restrictions
- No wildcard permissions granted

**Test Coverage:**
- ✅ Lambda function construct exists verification
- ✅ Lambda has Python 3.12 runtime verification
- ✅ Lambda has handler configured verification
- ✅ Lambda has environment variables (METADATA_TABLE_NAME) verification
- ✅ Lambda execution role has DynamoDB permissions verification
- ✅ Lambda execution role has CloudWatch Logs permissions verification
- ✅ State machine role has Lambda invoke permissions verification
- ✅ State machine includes Lambda invocation task verification

**Architecture Updates:**
- ✅ Mermaid diagram updated to show Lambda function in workflow
- ✅ Lambda positioned between DynamoDB write and Polly in flow
- ✅ Lambda highlighted as implemented skeleton with green styling
- ✅ CloudWatch Logs connection from Lambda shown
- ✅ Error handling path includes Lambda task
- ✅ Implementation status section updated to reflect Issue #7 completion

**TDD Approach (Strict):**
- ✅ Tests written first (8 new tests)
- ✅ Tests failed initially (expected behavior)
- ✅ Minimal implementation added to pass tests
- ✅ All tests pass (36/36 total)
- ✅ CDK synth successful
- ✅ No regressions in existing tests

**Next Steps (Issue #8):**
- Complete pipeline wiring with input validation
- Implement actual audio validation logic in Lambda
- Add audio metadata extraction (duration, format, sample rate)
- Implement S3 output persistence
- Add end-to-end flow testing
- Consider adding DynamoDB update capability to Lambda if needed

---

### Issue #8: TDD: Complete Pipeline Wiring, Input Validation & Basic End-to-End Flow (✅ Completed)

**Goal:**
Wire together all components into a complete basic pipeline with input validation and clean end-to-end flow.

**Implemented Features:**

1. **Lambda Input Validation**
   - Added `validate_input()` function to Lambda handler
   - Validates required fields: `detail`, `bucket.name`, `object.key`
   - Validates field values are non-empty (strips whitespace)
   - Validates file extensions: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`
   - Custom `ValidationError` exception class
   - Detailed error messages with supported format list
   - Returns structured error responses: `{status: 'error', errorType: 'ValidationError', message: '...'}`

2. **Complete End-to-End Flow**
   - **Success Path:**
     1. S3 upload → EventBridge → Step Functions
     2. Write initial metadata (status=PROCESSING)
     3. Lambda validates input (passes validation)
     4. Polly task executes (skeleton)
     5. Update status (status=COMPLETED)
     6. Publish success notification
   - **Failure Path:**
     1. Any error caught by Catch blocks
     2. Update status (status=FAILED with error details)
     3. Publish failure notification
   - **Validation Failure Path:**
     1. Lambda validation fails
     2. Returns error response
     3. Triggers failure path via error handling
     4. Status updated to FAILED
     5. Failure notification published

3. **Comprehensive Test Suite**
   - **CDK Infrastructure Tests (43 tests):**
     - All existing tests continue to pass
     - 7 new Issue #8 tests for:
       - State machine validation state presence
       - Complete success path verification
       - Complete failure path verification
       - EventBridge to Step Functions integration
       - IAM least-privilege verification
       - Complete stack snapshot test
       - Lambda validation capability
   - **Lambda Validation Tests (8 tests):**
     - Missing detail field → error
     - Missing bucket name → error
     - Missing object key → error
     - Unsupported file extensions (.txt, .exe, .zip, .pdf, .jpg) → error
     - Supported file extensions (.mp3, .wav, .m4a, .ogg, .flac) → success
     - Empty bucket name → error
     - Empty object key → error
     - Validation error type verification

4. **Documentation Updates**
   - Updated status header to "Issue #8 completed"
   - Refined Mermaid diagram:
     - Added validation check node (yellow diamond)
     - Highlighted error paths (red styling)
     - Updated legend to show Issue #3-8 as implemented
     - Added validation flow arrows
   - Added comprehensive "End-to-End Flow Details" section (Section 5):
     - Success path step-by-step
     - Failure path step-by-step
     - Validation error scenarios table
   - Updated Implementation Progress checklist

**Security Features:**
- All IAM permissions follow least-privilege principles
- Lambda only has read-only DynamoDB access
- Step Functions has scoped permissions for specific resources
- EventBridge has dedicated IAM role
- No wildcard (*) resource permissions
- KMS encryption for SNS topics
- S3 encryption and private buckets

**Test Coverage:**
- ✅ 51 total tests passing (43 CDK + 8 Lambda validation)
- ✅ Lambda input validation for all error cases
- ✅ Lambda accepts all supported audio formats
- ✅ CDK stack synthesis successful
- ✅ IAM permissions verification
- ✅ Complete stack snapshot test
- ✅ End-to-end flow verification tests

**Architecture Updates:**
- ✅ Mermaid diagram includes validation node and error paths
- ✅ Updated legend to show Issue #3-8 implemented
- ✅ Added Section 5: End-to-End Flow Details
- ✅ Success, failure, and validation paths documented
- ✅ Validation error scenarios table added
- ✅ Implementation status updated to Issue #8 completed

**TDD Approach (Strict):**
1. ✅ **Tests written first:**
   - 7 new CDK tests added to `test_cdk_base_stack.py`
   - 8 new Lambda validation tests in `test_lambda_validation.py`
   - Initial run: 7 Lambda validation tests failed (as expected)
2. ✅ **Implementation added to pass tests:**
   - Added `validate_input()` function to Lambda
   - Added `ValidationError` exception class
   - Added supported audio extensions constant
   - Updated handler to call validation
   - Added specific error handling for ValidationError
3. ✅ **All tests pass:**
   - All 51 tests passing (43 CDK + 8 Lambda validation)
   - CDK synth successful
   - No regressions in existing tests
4. ✅ **Documentation updated:**
   - ARCHITECTURE.md comprehensively updated
   - Mermaid diagram refined
   - End-to-end flow documented

**Validation Rules Implemented:**

| Rule | Check | Error Message |
|------|-------|---------------|
| Required field: detail | `'detail' in event` | "Missing required 'detail' field in event" |
| Required field: bucket.name | `detail.get('bucket', {}).get('name', '').strip()` | "Missing or empty bucket name in event" |
| Required field: object.key | `detail.get('object', {}).get('key', '').strip()` | "Missing or empty object key in event" |
| Supported audio format | `extension in {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}` | "Unsupported audio format '.ext'. Supported formats: ..." |

**Pipeline Wiring Status:**
- ✅ EventBridge → Step Functions: Full event payload passed
- ✅ Step Functions → DynamoDB: Initial metadata write with event data
- ✅ Step Functions → Lambda: Event payload with detail and metadata
- ✅ Lambda → Validation: Input validation with clear error paths
- ✅ Lambda → Polly: Success path continues to Polly task
- ✅ Polly → DynamoDB: Status update to COMPLETED
- ✅ DynamoDB → SNS: Success notification published
- ✅ Error paths → DynamoDB: Status update to FAILED with error details
- ✅ Error paths → SNS: Failure notification published
- ✅ All tasks → CloudWatch: Comprehensive logging

**Next Steps (Issue #9):**
- Pipeline testing and refinement
- Integration testing with actual S3 events
- Performance optimization if needed
- Additional metadata extraction (file size, duration)
- S3 output persistence implementation
- Deployment preparation and environment-specific configuration
