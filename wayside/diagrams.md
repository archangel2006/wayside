# Wayside diagrams

Paste any block into `README.md` or `docs/`. GitHub renders Mermaid code fences. For DEV, export a diagram as an image if the fence does not render.

## 1. Architecture

```mermaid
flowchart LR
  subgraph Browser["Phone or laptop browser"]
    UI["static/index.html"]
    DB[("IndexedDB<br/>albums, cutouts, stories")]
  end

  subgraph Space["Hugging Face Space: Docker, free CPU"]
    API["FastAPI app<br/>stateless"]
    CUT["rembg<br/>cutouts"]
    VIS["Small vision model<br/>labels"]
    LLM["Small language model<br/>stories, challenges"]
    IMG["Small image model<br/>story covers"]
  end

  HUB["Hugging Face Hub<br/>model weights"]

  UI <--> DB
  UI -->|"HTTPS"| API
  API --> CUT
  API --> VIS
  API --> LLM
  API --> IMG
  HUB -.->|"downloaded at build"| API
```

## 2. User flow

```mermaid
flowchart TD
  A([Open Wayside]) --> B[Loading screen]
  B --> C[Landing page]
  C --> D[Collect page]
  D --> E[See a challenge]
  E --> F{Found something?}
  F -->|No| G[Tap for another idea]
  G --> E
  F -->|Yes| H[Snap a photo]
  H --> I[Background cut out]
  I --> J[Find named and described]
  J --> K[Glass box added to this walk]
  K --> L{More to collect?}
  L -->|Yes| E
  L -->|No| M[End walk and name it]
  M --> N[Saved to Albums in the browser]
  N --> O[Open the walk]
  O --> P[Tick finds, add notes]
  P --> Q[Pick a theme and setting]
  Q --> R[Language model writes a story]
  R --> CV[Optional: make a cover image]
  CV --> S{Keep it?}
  S -->|Try again| R
  S -->|Save| T[(Story vault)]
  T --> U[Read or listen later in Stories]
```

## 3. Page map

```mermaid
flowchart LR
  LOAD["Loading"] --> LAND["Landing"]
  LAND -->|"Start a walk"| COL

  subgraph APP["App with sidebar or tab bar"]
    COL["Collect"]
    ALB["Albums"]
    STR["Stories"]
    SET["Settings"]
    TRIP["Trip<br/>grid, story builder, vault"]
  end

  COL -->|"End walk"| TRIP
  ALB --> TRIP
  STR -->|"Open walk"| TRIP
  TRIP -->|"Back"| ALB
  SET -->|"Pick a theme"| SET
  SET -->|"Replay intro"| LOAD
  APP -->|"About Wayside"| LAND
```

## 4. Snap a photo

```mermaid
sequenceDiagram
  actor U as You
  participant UI as Browser
  participant API as FastAPI on the Space
  participant R as rembg
  participant V as Vision model
  participant DB as IndexedDB

  U->>UI: Take or pick a photo
  par Cut out
    UI->>API: POST /api/cutout
    API->>R: Remove background
    R-->>API: Transparent PNG
    API-->>UI: Cutout
  and Name it
    UI->>API: POST /api/label
    API->>V: Ask for label as JSON
    V-->>API: label and description
    API-->>UI: Label
  end
  UI->>DB: Save the find
  UI-->>U: New glass box appears
```

## 5. Write a story

```mermaid
sequenceDiagram
  actor U as You
  participant UI as Browser
  participant API as FastAPI on the Space
  participant L as Language model
  participant DB as IndexedDB

  U->>UI: Tick finds, set theme and setting
  UI->>API: POST /api/story with items, notes, theme, place
  API->>L: Prompt with labels, notes, tone
  L-->>API: Title and story text
  API-->>UI: Story
  UI-->>U: Read or listen
  U->>UI: Save to vault
  UI->>DB: Store story with the walk
```

## 6. Make a cover

```mermaid
sequenceDiagram
  actor U as You
  participant UI as Browser
  participant API as FastAPI on the Space
  participant I as Image model
  participant DB as IndexedDB

  U->>UI: Tap Make cover
  UI->>API: POST /api/cover with title, theme, place, labels (text only)
  API->>I: Text prompt, few denoising steps
  I-->>API: Image
  API-->>UI: PNG
  UI->>DB: Store cover with the story
  UI-->>U: Cover appears on the story
```

## 7. Request lifecycle on a busy server

```mermaid
flowchart TD
  R([Request arrives]) --> V{Valid image or input?}
  V -->|No| E1[400 with a short message]
  V -->|Yes| RL{Under the rate limit?}
  RL -->|No| E2[429 slow down]
  RL -->|Yes| Q{Queue short enough?}
  Q -->|No| E3[503 busy, try again]
  Q -->|Yes| M[Wait for the model lock]
  M --> RUN[Run the model]
  RUN --> OK{Valid output?}
  OK -->|No| RETRY[Retry once, then use a fallback]
  OK -->|Yes| DONE([Return result, store nothing])
  RETRY --> DONE
```

## 8. Data model (stored in the browser)

```mermaid
erDiagram
  TRIP ||--o{ ITEM : contains
  TRIP ||--o{ STORY : has

  TRIP {
    string id
    string name
    string date
    string place
  }
  ITEM {
    string id
    blob cutout
    string label
    string description
    string note
    int tilt
  }
  STORY {
    string id
    string title
    string theme
    string text
    blob cover
  }
```
