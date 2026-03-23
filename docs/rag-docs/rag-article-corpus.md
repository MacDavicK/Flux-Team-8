# Flux RAG Article Corpus

Reference documentation for the 30 curated expert articles used by the Flux
RAG pipeline (SCRUM-46). These articles are ingested into the Pinecone vector
store and retrieved by the Goal Planner agent (SCRUM-47) to ground its
recommendations in evidence-based guidance.

## Overview

| Metric | Value |
|---|---|
| Total articles | 30 |
| Categories | 5 (weight_loss, nutrition, strength, cardio, behavioral) |
| Articles per category | 6 |
| Authority types | government, peer_reviewed, hospital, university |
| Vector store | Pinecone (`flux-articles`, 1536 dims, cosine) |
| Embedding model | `openai/text-embedding-3-small` via OpenRouter |

## Article File Format

Each `.txt` file in `backend/articles/` uses this header format:

```
Title: <title> | Source: <url>
Category: <category> | Authority: <authority>
---
<body text>
```

## Article Registry

### Category 1: Weight Loss & Healthy Weight (6)

| # | File | Title | Authority |
|---|---|---|---|
| 01 | `01_nhlbi_aim_healthy_weight.txt` | Aim for a Healthy Weight | government |
| 02 | `02_cdc_steps_losing_weight.txt` | Steps for Losing Weight | government |
| 03 | `03_who_obesity_overweight.txt` | Obesity and Overweight Fact Sheet | government |
| 04 | `04_mayo_weight_loss_6_strategies.txt` | Weight Loss: 6 Strategies for Success | hospital |
| 05 | `05_pmc_prevention_obesity_evidence.txt` | Prevention of Obesity among Adults: Evidence | peer_reviewed |
| 06 | `06_pmc_rate_weight_loss_prediction.txt` | Rate of Weight Loss Can Be Predicted by Patient Characteristics | peer_reviewed |

### Category 2: Diet & Nutrition (6)

| # | File | Title | Authority |
|---|---|---|---|
| 07 | `07_who_healthy_diet.txt` | Healthy Diet Fact Sheet | government |
| 08 | `08_pmc_optimal_diet_strategies.txt` | Optimal Diet Strategies for Weight Loss and Maintenance | peer_reviewed |
| 09 | `09_ucdavis_weight_loss_guidelines.txt` | Helpful Guidelines for Successful Weight Loss | university |
| 10 | `10_harvard_healthy_eating_plate.txt` | Healthy Eating Plate | university |
| 11 | `11_usda_dietary_guidelines_2020.txt` | Dietary Guidelines for Americans 2020-2025 Executive Summary | government |
| 12 | `12_harvard_water_intake.txt` | Water: How Much Do You Need? | university |

### Category 3: Physical Activity & Strength Training (6)

| # | File | Title | Authority |
|---|---|---|---|
| 13 | `13_hhs_physical_activity_guidelines.txt` | Physical Activity Guidelines for Americans | government |
| 14 | `14_who_physical_activity.txt` | Physical Activity Fact Sheet | government |
| 15 | `15_acsm_resistance_training.txt` | Resistance Training for Health and Fitness | government |
| 16 | `16_healthdirect_strength_beginners.txt` | Strength Training for Beginners | government |
| 17 | `17_msu_acsm_recommendations.txt` | Evidence-Based Physical Activity Recommendations Part 2 | university |
| 18 | `18_kaiser_strength_beginners.txt` | Beginners Guide: Simple Strength Training Exercises | hospital |

### Category 4: Running & Cardio (6)

| # | File | Title | Authority |
|---|---|---|---|
| 19 | `19_nhs_couch_to_5k.txt` | Couch to 5K Running Plan | government |
| 20 | `20_mayo_5k_training.txt` | 5K Run: 7-Week Training Schedule for Beginners | hospital |
| 21 | `21_pmc_start_to_run_6week.txt` | Effectiveness of Start to Run: 6-Week Training Program | peer_reviewed |
| 22 | `22_jama_aerobic_dose_response.txt` | Aerobic Exercise and Weight Loss Dose-Response Meta-Analysis | peer_reviewed |
| 23 | `23_healthdirect_running_tips.txt` | Running Tips for Beginners | government |
| 24 | `24_pmc_progressive_overload.txt` | Progressive Overload Without Progressing Load | peer_reviewed |

### Category 5: Behavioral & Lifestyle (6)

| # | File | Title | Authority |
|---|---|---|---|
| 25 | `25_pmc_habit_formation_meta.txt` | Time to Form a Habit: Systematic Review and Meta-Analysis | peer_reviewed |
| 26 | `26_pmc_sleep_deprivation_weight.txt` | Sleep Deprivation: Effects on Weight Loss | peer_reviewed |
| 27 | `27_cdc_about_sleep.txt` | About Sleep | government |
| 28 | `28_cleveland_stress_weight.txt` | Long-Term Stress Can Make You Gain Weight | hospital |
| 29 | `29_pmc_self_monitoring_review.txt` | Self-Monitoring in Weight Loss: A Systematic Review | peer_reviewed |
| 30 | `30_pmc_behavioral_treatment_obesity.txt` | Behavioral Treatment of Obesity | peer_reviewed |

## Ingestion Pipeline

The ingestion pipeline (`backend/app/services/rag_service.py`) processes
articles in four stages:

1. **Load** — Read `.txt`/`.md` files from the articles directory, parse
   the 2-line metadata header (title, source, category, authority).
2. **Chunk** — Split article bodies using `RecursiveCharacterTextSplitter`
   (2000 chars, 200 overlap).
3. **Embed** — Batch-embed chunks via OpenRouter using
   `openai/text-embedding-3-small` (1536 dimensions).
4. **Upsert** — Store vectors in Pinecone with metadata (text, title,
   source, chunk_index, category, authority).

## Admin Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/rag/ingest` | Run the full ingestion pipeline |
| GET | `/api/v1/rag/search?q=...` | Debug search endpoint |

## Download Script

`backend/scripts/download_articles.py` is a standalone utility that
downloads all 30 articles from their original sources. It is not part
of the FastAPI application runtime.

```bash
cd backend/scripts
pip install requests beautifulsoup4 lxml pdfplumber
python download_articles.py
```

## Notes

- Articles 01, 10, 11, 12, 13, and 22 were manually written/supplemented
  after the original download script encountered 403 errors or JS-rendered
  pages that returned insufficient content.
- Article 22 (JAMA) uses an equivalent PMC article (PMC3925973) on aerobic
  exercise and weight loss as a substitute.
