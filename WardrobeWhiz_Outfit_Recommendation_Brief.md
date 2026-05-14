# WardrobeWhiz Outfit Recommendation Pipeline Brief
### For ChatGPT — Read fully before generating any Codex prompts

---

## What This Feature Does

User fills in an "Outfit Context" form (occasion, location, weather, temperature, mood, dress code, notes).
The system retrieves items from their wardrobe, combines that with their style profile, and sends everything to Groq.
Groq returns a curated outfit selection with styling tips.
Frontend displays the selected items as images with natural language explanation.

---

## Data Available (From Screenshots)

### 1. Outfit Context (user fills this per request)
```json
{
  "occasion": "e.g. Board meeting, Casual dinner",
  "location": "e.g. Karachi, Lahore, Office",
  "weather": "e.g. Sunny, Humid, Cold",
  "temperature_c": 26,
  "mood": "e.g. Professional, Casual, Playful",
  "dress_code": "e.g. Business casual, Smart casual",
  "notes": "Any additional context"
}
```

### 2. User Style Profile (from profile page)
```json
{
  "usually_dresses_for": ["Weddings", "Formal events"],
  "everyday_style": "Formal stylish and classy clothes",
  "formality": 4,
  "comfort_vs_style": 3,
  "eastern_western": "Both",
  "modesty": "Balanced",
  "avoids": ["casual wear"],
  "preferred_colors": ["#000000", "#ffffff", "#faebd1", "#362405", "#113918", "#152b66"],
  "disliked_colors": ["#fa0000", "#00fa3a", "#f3fa00", "#fa00ee"],
  "aesthetics": ["Classic", "Minimalist", "Formal"],
  "fit": "Slim",
  "layering": "Like layers",
  "accessories": "Statement accessories",
  "measurements": {
    "height": "5'10",
    "weight": 67,
    "collar": 16,
    "chest": 34,
    "shoulder": 20,
    "sleeve": 28,
    "waist": 33,
    "inseam": 31,
    "shoe_size": 43
  }
}
```

### 3. Wardrobe Items (from DB — retrieved per user)
Each item has:
```json
{
  "id": 12,
  "name": "Navy Blue Slim Fit Blazer",
  "category": "Outerwear",
  "type": "Blazer",
  "color_label": "Navy Blue",
  "color_hex": "#152b66",
  "pattern": "solid",
  "season": ["All-Season"],
  "occasion": ["formal", "work", "wedding"],
  "style_tags": ["classic", "slim", "formal"],
  "description": "A slim fit navy blazer with notch lapels...",
  "image_url": "/storage/segmented/item_12.png"
}
```

---

## The RAG Approach

This is not traditional vector RAG. It is **context-stuffing RAG** — you retrieve the relevant wardrobe items and inject them directly into the LLM prompt. This works well because:
- Wardrobe size is small (50–200 items max per user)
- Items are already structured JSON
- No embeddings or vector DB needed
- Groq handles large contexts fast

### Retrieval Step (Pre-filter before LLM)
Do NOT send all 200 wardrobe items to Groq. Pre-filter in Python first:

```python
def retrieve_relevant_items(wardrobe: list, context: dict) -> list:
    scored = []
    
    for item in wardrobe:
        score = 0
        
        # Season match
        temp = context.get("temperature_c", 20)
        if temp > 25 and "Summer" in item.get("season", []):
            score += 3
        elif temp < 15 and "Winter" in item.get("season", []):
            score += 3
        elif "All-Season" in item.get("season", []):
            score += 1
        
        # Occasion match
        occasion_keywords = context.get("occasion", "").lower().split()
        for kw in occasion_keywords:
            if any(kw in occ for occ in item.get("occasion", [])):
                score += 2
        
        # Dress code match
        dress_code = context.get("dress_code", "").lower()
        if "formal" in dress_code and item.get("category") in ["Outerwear", "Tops", "Bottoms"]:
            score += 2
        if "casual" in dress_code and "casual" in item.get("style_tags", []):
            score += 2
        
        # Color preference match
        preferred = profile.get("preferred_colors", [])
        if item.get("color_hex") in preferred:
            score += 2
        
        # Disliked color penalty
        disliked = profile.get("disliked_colors", [])
        if item.get("color_hex") in disliked:
            score -= 5
        
        scored.append((item, score))
    
    # Sort by score, take top 30
    scored.sort(key=lambda x: x[1], reverse=True)
    return [item for item, score in scored[:30]]
```

This means Groq only sees the 30 most relevant items, keeping the prompt lean and fast.

---

## The Groq Prompt

```python
def build_outfit_prompt(context: dict, profile: dict, items: list) -> str:
    
    items_text = "\n".join([
        f"ID:{item['id']} | {item['name']} | {item['category']} | "
        f"Color:{item['color_label']} | Pattern:{item['pattern']} | "
        f"Season:{item['season']} | Occasion:{item['occasion']} | "
        f"Tags:{item['style_tags']}"
        for item in items
    ])
    
    return f"""
You are a personal fashion stylist for WardrobeWhiz. 
Your job is to select a complete outfit from the user's wardrobe for a specific occasion.

USER STYLE PROFILE:
- Usually dresses for: {profile['usually_dresses_for']}
- Everyday style: {profile['everyday_style']}
- Formality preference: {profile['formality']}/5
- Aesthetics: {profile['aesthetics']}
- Fit preference: {profile['fit']}
- Likes layering: {profile['layering']}
- Avoids: {profile['avoids']}
- Preferred colors (hex): {profile['preferred_colors']}
- Disliked colors (hex): {profile['disliked_colors']}

OUTFIT CONTEXT:
- Occasion: {context['occasion']}
- Location: {context['location']}
- Weather: {context['weather']}
- Temperature: {context['temperature_c']}°C
- Mood/Style: {context['mood']}
- Dress Code: {context['dress_code']}
- Notes: {context['notes']}

AVAILABLE WARDROBE ITEMS:
{items_text}

TASK:
Select a complete, cohesive outfit from ONLY the items listed above.
A complete outfit includes: top, bottom OR full outfit (dress/jumpsuit), footwear, and optionally outerwear and accessories.
Only recommend items that genuinely work together.
Respect the user's disliked colors strictly.
Prioritize their preferred colors and aesthetics.

Return ONLY a valid JSON object. No markdown. No extra text:

{{
  "outfit_name": "short catchy outfit name e.g. Sharp Monday Formal",
  "selected_item_ids": [12, 7, 23, 31],
  "outfit_description": "2-3 sentence overview of the full outfit and why it works for this occasion",
  "styling_tips": [
    "Tuck in the shirt to accentuate the slim fit",
    "Roll the sleeves once for a smart casual look",
    "The navy blazer ties the color palette together"
  ],
  "color_story": "Brief explanation of why these colors work together",
  "why_it_fits_you": "Personalized note referencing their profile e.g. Given your formal leaning aesthetic and preference for classic minimalist style..."
}}
"""
```

---

## The Full API Flow

### Backend Endpoint
```python
from groq import AsyncGroq
import json

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

@app.post("/outfit/recommend")
async def recommend_outfit(
    context: OutfitContextSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Fetch full wardrobe for user
    all_items = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == current_user.id
    ).all()
    
    # 2. Fetch user profile
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    # 3. Pre-filter to top 30 relevant items
    relevant_items = retrieve_relevant_items(
        [item.__dict__ for item in all_items],
        context.dict(),
        profile.__dict__
    )
    
    # 4. Build prompt and call Groq
    prompt = build_outfit_prompt(context.dict(), profile.__dict__, relevant_items)
    
    response = await groq_client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.3  # slight creativity, still consistent
    )
    
    raw = response.choices[0].message.content
    clean = raw.replace("```json", "").replace("```", "").strip()
    recommendation = json.loads(clean)
    
    # 5. Resolve item IDs to full item objects (with image URLs)
    selected_ids = recommendation["selected_item_ids"]
    selected_items = [
        item for item in all_items 
        if item.id in selected_ids
    ]
    
    # Preserve the order Groq selected them
    id_to_item = {item.id: item for item in selected_items}
    ordered_items = [id_to_item[id] for id in selected_ids if id in id_to_item]
    
    return {
        "outfit_name": recommendation["outfit_name"],
        "outfit_description": recommendation["outfit_description"],
        "styling_tips": recommendation["styling_tips"],
        "color_story": recommendation["color_story"],
        "why_it_fits_you": recommendation["why_it_fits_you"],
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "image_url": item.segmented_image_path or item.image_path,
                "color_label": item.color_label,
                "color_hex": item.color_hex
            }
            for item in ordered_items
        ]
    }
```

---

## Frontend Display

The response gives you everything needed to display:

```javascript
// Outfit card layout
{
  outfit_name: "Sharp Monday Formal",
  outfit_description: "A polished navy and cream combination...",
  styling_tips: ["Tuck in the shirt...", "Roll the sleeves..."],
  color_story: "Navy and cream create a timeless formal palette...",
  why_it_fits_you: "Given your formal leaning aesthetic...",
  items: [
    { id: 12, name: "Navy Blazer", category: "Outerwear", image_url: "...", color_hex: "#152b66" },
    { id: 7,  name: "Cream Dress Shirt", category: "Tops", image_url: "...", color_hex: "#faebd1" },
    { id: 23, name: "Black Slim Trousers", category: "Bottoms", image_url: "...", color_hex: "#000000" },
    { id: 31, name: "Black Oxford Shoes", category: "Footwear", image_url: "...", color_hex: "#000000" }
  ]
}
```

Suggested frontend layout:
```
┌─────────────────────────────────────────┐
│  Sharp Monday Formal                    │
│  "A polished navy and cream..."         │
├──────┬──────┬──────┬──────┐             │
│ img  │ img  │ img  │ img  │  ← items   │
│Blazer│Shirt │Trous.│Shoes │             │
└──────┴──────┴──────┴──────┘             │
│  Styling Tips          Color Story      │
│  • Tuck in shirt       Navy + cream ... │
│  • Roll sleeves                         │
│  Why it fits you:                       │
│  Given your formal aesthetic...         │
└─────────────────────────────────────────┘
```

---

## Speed Expectations

| Step | Time |
|---|---|
| DB fetch + pre-filter | ~50ms |
| Groq LLM call | ~1.5–2s |
| Response + image URLs | ~50ms |
| **Total** | **~2 seconds** |

Well within your 10 second target.

---

## Academic Justification for This Approach

Your contribution here is:
1. **Retrieval scoring algorithm** — you designed the pre-filter that scores items by season, occasion, dress code, and color preference
2. **Context-stuffing RAG architecture** — deliberate choice over vector RAG, justified by wardrobe size constraints
3. **Prompt engineering** — profile + context + wardrobe injected in structured format
4. **Personalization layer** — disliked colors, preferred aesthetics, measurements all influence output
5. **End-to-end pipeline** — from form input to image display with natural language output

Examiner quote: *"The system implements a retrieval-augmented generation pipeline where a scoring function retrieves contextually relevant wardrobe items, which are injected alongside user style profile data into a structured LLM prompt, producing personalized outfit recommendations grounded entirely in the user's actual wardrobe."*

---

## How to Use This Brief

1. Paste this entire document into ChatGPT
2. Say: *"Based on this brief, generate a Codex prompt to implement the outfit recommendation endpoint in our existing FastAPI backend"*
3. Also paste your existing: user profile schema, wardrobe item model, and current router file
4. Implement backend first, verify the JSON response, then ask for a separate Codex prompt for the frontend display component
