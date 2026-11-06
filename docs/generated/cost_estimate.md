# Video-generation cost estimate (Google Veo 3.1, Gemini API)

Prices: 2026-10 (third-party summaries; verify before spending). Edit `pipeline/config.yaml` once you have checked the official pricing page.

- Shots: 90 (53 × 8 s base, 37 × 8 s base + 7 s extension)
- Seconds to generate per complete pass: **979 s** (final cut uses 900 s)
- AI video rarely nails every shot first time; budget for retakes. The ×2.5 column assumes an average of 2.5 takes per shot.

| Tier | Resolution | One pass | With retakes (×2.5) |
|---|---|---|---|
| standard | 720p | $392 | $979 |
| standard | 1080p | $392 | $979 |
| standard | 4k | $587 | $1,468 |
| fast | 720p | $98 | $245 |
| fast | 1080p | $117 | $294 |
| fast | 4k | $294 | $734 |
| lite | 720p | $49 | $122 |
| lite | 1080p | $78 | $196 |

Notes: extension only works at 720p and not on Lite, so the pipeline renders 720p and upscales to 1080p at assembly. Character reference sheets (~15 images) cost a few dollars at most.
