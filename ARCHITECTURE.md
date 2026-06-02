# Architecture — Event-Driven Sleep Audio Pipeline

> **Status:** **Core infrastructure implemented (Issue #3)**. Input/Output S3 buckets
> and EventBridge rule are now live. This document is the **single source of
> truth** for the system design. All future issues and pull requests must keep
> their implementation consistent with this file and update it when the design
> evolves.
> 
> **Implementation Progress:**
> - ✅ Issue #2: Design baseline established
> - ✅ Issue #3: Core S3 Buckets + EventBridge Rule (completed)
> - 🔜 Issue #4: Step Functions State Machine Skeleton + Polly Integration (next)

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
- ✅ = Implemented (Issue #3)
- 🔜 = Planned (Issue #4+)

```mermaid
flowchart TD
    user([User / Client App])

    subgraph ingestion["✅ Ingestion (Implemented)"]
        input[("✅ Input S3 Bucket\nSleepAudioInputBucket\nprivate · encrypted · versioned")]
        eb{{"✅ EventBridge Rule\nSleepAudioProcessingRule\nObject Created"}}
    end

    subgraph processing["🔜 Processing — AWS Step Functions (Planned)"]
        validate["🔜 Validate &amp; Extract Metadata\n(Lambda)"]
        polly["🔜 Amazon Polly\nText-to-Speech"]
        bedrock["🔜 Amazon Bedrock\nAI Soundscapes (optional)"]
        persist["🔜 Persist Processed Audio\n(Lambda)"]
    end

    subgraph storage["Storage &amp; State"]
        output[("✅ Output S3 Bucket\nSleepAudioOutputBucket\nprivate · encrypted · versioned")]
        ddb[("🔜 DynamoDB\nmetadata &amp; status")]
    end

    subgraph notify_obs["🔜 Notifications &amp; Observability (Planned)"]
        sns(["🔜 SNS Topic\ncompletion / error"])
        cw["✅ CloudWatch\nLogs (placeholder target)"]
    end

    user -->|1. upload raw audio| input
    input -->|2. Object Created event| eb
    eb -->|3. log event (temporary)| cw
    eb -.->|"3. start execution (Issue #4)"| validate
    validate -.->|4. status = PROCESSING| ddb
    validate -.->|5a. synthesize voice| polly
    validate -.->|5b. enhance / generate| bedrock
    polly -.-> persist
    bedrock -.-> persist
    persist -.->|6. write processed file| output
    persist -.->|7. status = COMPLETED / FAILED| ddb
    persist -.->|8. publish result| sns
    sns -.->|notify subscribers| user

    validate -.->|logs &amp; metrics| cw
    polly -.->|logs &amp; metrics| cw
    bedrock -.->|logs &amp; metrics| cw
    persist -.->|logs &amp; metrics| cw
    cw -.->|9. alarm on failure| sns
    
    style input fill:#90EE90
    style output fill:#90EE90
    style eb fill:#90EE90
    style cw fill:#90EE90
```

**Current Implementation (Issue #3):**
- ✅ Input and Output S3 buckets are created with encryption, versioning, and public access blocking
- ✅ EventBridge rule is configured to trigger on S3 Object Created events
- ✅ CloudWatch Logs serves as a temporary placeholder target for the EventBridge rule
- 🔜 Step Functions state machine will replace the CloudWatch Logs target in Issue #4

---

## 5. Security

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

## 6. Observability

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

## 7. Cost Considerations

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

## 8. Multi-Environment Support

Environments (`dev` / `stage` / `prod`) are selected through **CDK context**
(for example `cdk deploy -c env=dev`). The environment name drives:

- Resource naming / removal policies (e.g. `RETAIN` in prod, `DESTROY` in dev).
- Feature flags such as enabling the optional Bedrock branch.
- Log retention, alarm thresholds, and KMS key configuration.

Each environment synthesizes an isolated stack so changes can be promoted
`dev → stage → prod` safely.

---

## 9. Future Extensibility

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

## 10. Implementation Status

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

**Next Steps (Issue #4):**
- Replace CloudWatch Logs target with AWS Step Functions state machine
- Add validation Lambda function
- Integrate Amazon Polly for text-to-speech
