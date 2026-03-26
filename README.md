# WardrobeWhiz

An AI-powered personal wardrobe assistant that helps users generate outfit recommendations from their own clothing items using CLIP embeddings, FAISS vector search, and rule-based styling logic.

---

## Features

- **Wardrobe Upload** — upload clothing images; colors are extracted from pixels and category is inferred from filename
- **CLIP Embeddings** — each item is encoded into a 512-dim semantic vector using OpenAI's ViT-B/32 model
- **FAISS Retrieval** — fast k-NN vector search to find relevant items for any query
- **Guided Outfit Generation** — request outfits by occasion, mood, color preference, or free text
- **Surprise Me** — auto-generate random compatible outfit combinations
- **Feedback Loop** — like/dislike/skip/save outfits; preferences re-rank future suggestions automatically
- **Style Profile** — onboarding quiz stores preferred styles, colors, occasions, and Eastern/Western bias

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| Database | SQLite (via SQLAlchemy) |
| ML embeddings | CLIP (`open_clip_torch`, ViT-B/32) |
| Vector search | FAISS (`faiss-cpu`) |
| Image processing | Pillow |
| Validation | Pydantic v2 |
| Server | Uvicorn |

---

## Project Structure

```
Backend/
  app/
    main.py                  # App entry point, router registration, logging
    core/
      config.py              # Settings loaded from .env
      database.py            # SQLAlchemy engine + session
    models/                  # SQLAlchemy ORM models
      user.py
      profile.py
      wardrobe_item.py
      outfit.py
      feedback.py
    schemas/                 # Pydantic request/response schemas
      profile.py
      wardrobe.py
      outfit.py
      feedback.py
    api/routes/              # FastAPI route handlers
      health.py
      profile.py
      wardrobe.py
      outfits.py
      feedback.py
    services/                # Business logic
      profile_service.py     # User + profile CRUD, style vector generation
      image_service.py       # Upload pipeline: validate → save → thumbnail → colors → category
      embedding_service.py   # CLIP image/text embeddings (fallback to random if unavailable)
      faiss_service.py       # Per-user FAISS index: add, search, remove, rebuild
      retrieval_service.py   # Query → CLIP → FAISS → preference re-ranking → candidates
      outfit_service.py      # Guided + surprise outfit assembly, history
      wardrobe_service.py    # Wardrobe item CRUD
      feedback_service.py    # Feedback storage, preference stat aggregation
    utils/
      image_utils.py         # Validate, save, thumbnail helpers
      color_utils.py         # Dominant color extraction, compatibility scoring
      rules.py               # Category roles, outfit blueprints, explanation builder
    storage/
      uploads/               # Original uploaded images
      thumbnails/            # 256×256 JPEG thumbnails
      faiss/                 # Per-user FAISS index files (.index + _ids.json)
```

---

## Setup

### 1. Clone and navigate

```bash
git clone <repo-url>
cd wardrobewhiz/Backend
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> `torch` and `open_clip_torch` are large (~2 GB). If CLIP fails to load the app falls back to random embeddings so it still runs.

### 4. Create storage directories

```bash
mkdir -p app/storage/uploads app/storage/thumbnails app/storage/faiss
```

### 5. Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

### 6. Open API docs

```
http://localhost:8002/docs
```

---

## Environment Variables

All settings have defaults and the app runs without a `.env` file in local dev.

```env
APP_NAME=WardrobeWhiz API
DEBUG=true
DATABASE_URL=sqlite:///./wardrobewhiz.db
UPLOAD_DIR=app/storage/uploads
THUMBNAIL_DIR=app/storage/thumbnails
FAISS_DIR=app/storage/faiss
```

Override only what you need. For PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost/wardrobewhiz
```

---

## API Endpoints

### Health
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health/` | Server health check |

### Profiles
| Method | Endpoint | Description |
|---|---|---|
| POST | `/profiles/users` | Create a user |
| GET | `/profiles/users/{user_id}` | Get a user |
| POST | `/profiles/` | Create style profile |
| GET | `/profiles/{user_id}` | Get style profile |
| PUT | `/profiles/{user_id}` | Update style profile |

### Wardrobe
| Method | Endpoint | Description |
|---|---|---|
| POST | `/wardrobe/upload` | Upload a clothing image |
| GET | `/wardrobe/{user_id}` | List wardrobe items |
| GET | `/wardrobe/item/{item_id}` | Get single item |
| PUT | `/wardrobe/item/{item_id}` | Update item metadata |
| DELETE | `/wardrobe/item/{item_id}` | Delete item (also removes from FAISS) |

### Outfits
| Method | Endpoint | Description |
|---|---|---|
| POST | `/outfits/guided` | Generate outfit by occasion/mood/color |
| POST | `/outfits/surprise` | Generate random outfit combinations |
| GET | `/outfits/history/{user_id}` | Paginated outfit history |

### Feedback
| Method | Endpoint | Description |
|---|---|---|
| POST | `/feedback/` | Submit like/dislike/skip/save |
| GET | `/feedback/{user_id}` | Get feedback history and preference stats |

---

## How Image Identification Works

When you upload an image, three things happen:

| What | How | Used for |
|---|---|---|
| **Category** | Filename keyword matching | Outfit role assignment (top / bottom / shoes) |
| **Colors** | Pixel analysis → nearest named color | Color compatibility scoring |
| **CLIP embedding** | Neural network on image content | Similarity search via FAISS |

**Important:** Category is read from the filename, not the image content. Name your files descriptively before uploading:

```
black_shirt.jpg     → tops
blue_jeans.jpg      → bottoms
white_sneakers.jpg  → shoes
floral_dress.jpg    → dresses
red_jacket.jpg      → jackets
leather_bag.jpg     → accessories
```

If the filename has no recognizable keyword, category will be `null`. You can fix this after upload via `PUT /wardrobe/item/{item_id}`.

---

## End-to-End Test Flow

```
POST /profiles/users          → create user (save the id)
POST /profiles/               → create style profile
POST /wardrobe/upload         → upload clothing images (repeat 4-5x with top/bottom/shoes)
POST /outfits/guided          → request a guided outfit
POST /outfits/surprise        → request a surprise outfit
POST /feedback/               → like or dislike an outfit
GET  /feedback/{user_id}      → verify preferences were recorded
POST /outfits/guided          → suggestions are now re-ranked by your feedback
```

---

## MVP Scope

Completed for evaluation:

- [x] User profile + style quiz
- [x] Wardrobe image upload + metadata extraction
- [x] CLIP embeddings + FAISS indexing
- [x] Guided outfit generation
- [x] Surprise Me outfit generation
- [x] Like/dislike/skip/save feedback
- [x] Feedback-driven preference re-ranking

Future phases:

- [ ] User authentication
- [ ] Scraping + shop-the-look
- [ ] Reinforcement learning for ranking
- [ ] Advanced styling rules (weather, body type, fabric)
- [ ] Multi-agent orchestration
