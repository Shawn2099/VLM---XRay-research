# TrustMed — components and flow

v1 scope: **CXR-LLaVA generates · CheXbert extracts · DenseNet-121 verifies · calibrated confidence · human review.**
UI design language taken from `trustmed_prototype .zip`; nothing else from it.

## 1. Runtime flow (one report)

```mermaid
flowchart TD
    U["Clinician / radiologist<br/>browser"]:::actor

    subgraph WEB["TrustMed web — FastAPI :8002 · CPU"]
        AUTH["Auth + roles<br/>bcrypt · session cookie"]:::svc
        ING["Ingest<br/>decode · DICOM window · validate"]:::svc
        Q["Job queue<br/>one GPU at a time"]:::svc
        UI["Jinja + htmx UI<br/>upload · report · findings · review"]:::svc
        DB[("SQLite<br/>images · reports · findings<br/>reviews · audit_log")]:::store
    end

    G["CXR-LLaVA service :8000<br/>GPU · 13.2 GiB · 1.96 s"]:::gpu

    subgraph VER["Verifier — inside TrustMed, CPU"]
        C1["CheXbert<br/>report text → 14 labels<br/>+ sentence span"]:::ver
        C2["DenseNet-121<br/>image → 14 probabilities"]:::ver
        VD["Verdict engine<br/>supported · uncertain · unsupported<br/>contradiction · omission"]:::ver
        CF["Confidence<br/>severity-weighted support<br/>→ isotonic → 0…1"]:::ver
    end

    U -->|upload| AUTH --> ING
    ING -->|8-bit windowed image| DB
    ING --> Q
    Q -->|POST /report| G
    G -->|report text| C1
    ING -->|same windowed image| C2
    C1 --> VD
    C2 --> VD
    VD --> CF
    VD --> DB
    CF --> DB
    DB --> UI
    UI -->|accept · edit · reject| RV["Review workflow"]:::svc
    RV --> DB
    UI --> U

    classDef actor fill:#dff0f0,stroke:#0e6f73,color:#16212a
    classDef gpu fill:#16212a,stroke:#16212a,color:#ffffff
    classDef svc fill:#ffffff,stroke:#9fb3bb,color:#16212a
    classDef ver fill:#fdf0d8,stroke:#e0a23a,color:#16212a
    classDef store fill:#e1f2e8,stroke:#216b45,color:#16212a
```

## 2. Verdict engine (the core rule)

```mermaid
flowchart LR
    R["report finding<br/>CheXbert label"] --> J{"join by label"}
    P["image probability<br/>DenseNet"] --> J
    J --> D{"report says<br/>positive?"}
    D -->|yes| T1{"p ≥ 0.70"} -->|yes| S1["✓ supported"]
    T1 -->|0.30–0.70| S2["⚠ uncertain"]
    T1 -->|≤ 0.30| S3["✗ unsupported"]
    D -->|negative| T2{"p ≥ 0.70"} -->|yes| S4["✗✗ contradiction"]
    T2 -->|no| S5["✓ supported"]
    D -->|not mentioned| T3{"p ≥ 0.70"} -->|yes| S6["○ omission candidate"]
    T3 -->|no| S7["· not assessable"]
```

## 3. Offline calibration + evaluation (run once, before demo)

```mermaid
flowchart LR
    O["OpenI-500<br/>images + reference reports"]:::data
    O --> GEN["CXR-LLaVA"]:::gpu
    O --> DN["DenseNet-121"]:::ver
    O --> REF["CheXbert on reference"]:::ver
    GEN --> HYP["CheXbert on generated"]:::ver
    REF --> FIT["per-finding thresholds · Platt"]:::fit
    DN --> FIT
    HYP --> CONF["confidence model<br/>logistic + isotonic"]:::fit
    REF --> CONF
    FIT --> ART[("calibration.json")]:::store
    CONF --> ART
    ART --> RT["runtime confidence"]:::svc
    HYP --> EVAL["P/R · risk–coverage · ECE · AUC"]:::fit
    REF --> EVAL
```

## 4. Component responsibilities

| Component | Does | Does not |
|---|---|---|
| Ingest | decode, window, invert MONOCHROME1, validate, hash | generate anything |
| Generator client | call `/report`, record model + prompt hash + seed | interpret the text |
| CheXbert | report → labels + which sentence | see the image |
| DenseNet-121 | image → 14 probabilities | read the report |
| Verdict engine | join the two, emit 5 verdicts + severity | learn anything |
| Confidence | verdicts → calibrated 0…1 | invent features |
| Review | store human decision, immutable | change the report |
| UI | show *why*, not just *what* | decide |

## 5. From the zip — UI only

**Taken:** the palette (`--paper/--teal/--ok/--warn`), dark header + warning notice, left rail (upload · threshold · pipeline with `ms` tags), dual viewer with film captions, score bar with threshold tick, highlighted report sentences, findings bar list, focus rings, reduced-motion handling.

**Not taken:** template report bank, DenseNet-as-generator, seeded simulation, `Verified` wording, 10 MB/JPEG-only limits.
