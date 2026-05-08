# WardrobeWhiz — AI-Powered Smart Wardrobe & Outfit Recommendation System

## Overview

WardrobeWhiz is an AI-powered wardrobe management and outfit recommendation platform.

The system allows users to:

* Upload clothing images
* Automatically segment garments from backgrounds
* Extract metadata such as category, subcategory, color, season, and description
* Correct AI-generated metadata using a human-in-the-loop workflow
* Store wardrobe items digitally
* Generate outfit recommendations based on outfit context such as occasion, weather, mood, and dress code

The project currently focuses on:

* Computer vision based wardrobe ingestion
* Metadata extraction and correction
* Context-aware outfit recommendation groundwork
* Modular recommendation engine architecture

---

# Current Features

## Wardrobe Ingestion Pipeline

Users can upload clothing images.

The backend pipeline:

1. Validates image uploads
2. Removes background using segmentation
3. Extracts dominant garment colors
4. Classifies garment category and subcategory
5. Generates initial garment descriptions
6. Stores metadata in the database
7. Generates segmented images for cleaner wardrobe rendering

---

## Human-in-the-Loop Metadata Correction

After upload, users can edit:

* Name
* Category
* Subcategory
* Color
* Season
* Description

This improves:

* Accuracy
* Data quality
* Recommendation quality
* Real-world usability

---

## Outfit Generation

The outfit generation system currently uses:

* Query-aware retrieval
* Metadata matching
* Rule-based recommendation logic

Context fields currently include:

* Occasion
* Location
* Weather
* Temperature
* Mood/style
* Dress code
* Additional notes

Current outfit generation is functional but still under active improvement.

Planned improvements:

* Stronger outfit constraints
* Better occasion matching
* Weather-aware filtering
* Color compatibility scoring
* User profile personalization
* Feedback-based reranking

---

# Tech Stack

## Backend

* FastAPI
* SQLAlchemy
* SQLite (development)
* Python

## Frontend

* React
* TypeScript
* TailwindCSS

## AI / Computer Vision

* rembg / U2Net for segmentation
* CLIP-style embeddings and metadata matching
* Rule-based recommendation engine

---

# Project Structure

```text
WardrobeWiz_Codebase/
│
├── Backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── storage/
│   │   └── main.py
│   └── requirements.txt
│
├── Frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
└── README.md
```

---

# Setup Instructions

## 1. Clone Repository

```bash
git clone https://github.com/Taimoor-Mohsin/wardrobewhiz.git
cd wardrobewhiz
```

---

# Backend Setup

## 2. Navigate to Backend

```bash
cd Backend
```

## 3. Create Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Mac/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Run Backend

```bash
uvicorn app.main:app --reload --port 8002
```

Backend runs at:

```text
http://localhost:8002
```

---

# Frontend Setup

## 6. Navigate to Frontend

Open another terminal:

```bash
cd Frontend
```

---

## 7. Install Frontend Dependencies

```bash
npm install
```

---

## 8. Run Frontend

```bash
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

---

# Environment Notes

Current development environment:

* SQLite database
* Local file storage
* Local segmented image generation

Storage folders:

* uploads/
* segmented/
* thumbnails/

These are ignored in Git.

---

# Current Known Issues

The following are currently under active improvement:

## Outfit Recommendation

* Occasion matching still needs stronger constraints
* Weather filtering needs improvement
* Some invalid outfit structures can still occur
* Color compatibility scoring is still basic

## Classification

* Some subcategory predictions still require refinement
* Taxonomy consistency needs improvement (e.g. hoodie handling)

## User System

* User authentication not finalized
* Style profiling quiz still incomplete
* Feedback system not implemented yet

---

# Planned Improvements

## Recommendation Engine

* Constraint-based outfit validation
* Occasion-aware filtering
* Weather-aware filtering
* Color compatibility matrix
* Structured outfit templates

## User Personalization

* Style quiz
* User profiles
* Preferred colors/styles
* Item-level feedback
* Outfit-level feedback

## AI Improvements

* Better fashion subcategory classification
* Pattern recognition
* Improved description generation

---

# Git Workflow

## Main Working Branch

Current collaborative development branch:

```bash
dev
```

## Recommendation Engine Branch

Recommended branch for recommendation engine work:

```bash
recommendation-engine
```

---

# Recommended Git Commands

## Pull Latest Changes

```bash
git checkout dev
git pull origin dev
```

## Create Feature Branch

```bash
git checkout -b feature-name
```

## Push Changes

```bash
git add .
git commit -m "Describe changes"
git push origin branch-name
```

---

# Team Notes

Current focus should be:

1. Outfit recommendation intelligence
2. Context-aware recommendation constraints
3. Profile and personalization system
4. Feedback pipeline
5. Taxonomy consistency

The vision ingestion pipeline is now significantly more stable than earlier builds.

---

# Authors

WardrobeWhiz Final Year Project

Developed by:

* Taimoor Mohsin
* Team Members

---

# License

Academic Final Year Project — Educational Use
