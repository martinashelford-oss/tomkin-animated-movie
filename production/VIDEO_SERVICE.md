# Video-generation service: recommendation and costs

*Researched 6 November 2026. Prices change often, so confirm them on the provider's pricing page before approving. **No money has been spent and no API has been called.***

## What the film needs from a service
- **90 moving clips of 10 seconds each**, 3D CGI, 16:9, ideally 1080p, 24 fps.
- **Character consistency across 90 shots**: reference-image or "element" support for Tomkin, Penny, the Rigger, the drones and the leviathan.
- **An API**, so jobs can run from `production/generated/video_jobs.jsonl` instead of 90 manual uploads.
- **Silent output.** Voices, effects and music are mixed separately (see `PRODUCTION_WORKFLOW.md`), so the voices stay consistent from shot to shot.

## Recommendation: Kling 3.0 (Omni / reference-to-video)
| Why | |
|---|---|
| **Native 10-second clips** | They match the 90 × 10 s plan exactly, with no extensions or trimming. |
| **Reference "elements"** | Several reference images per character keep Tomkin's sock toque, Penny's apron and the Rigger's suit on-model. |
| **1080p output** | It meets the `CLAUDE.md` delivery spec without upscaling. |
| **Reasonable cost** | See the estimates below. |

**Runner-up: Google Veo 3.1 Fast** (1080p, up to three reference images, strong motion). It generates at most 8 seconds at a time, so every shot needs an extension, which roughly adds 60 % to the billed seconds and adds a visible join risk at the 8-second mark.

**Not available:** OpenAI Sora 2. OpenAI discontinued the Sora app (April 2026) and its API (reported 24 September 2026).

## Cost estimate (`python scripts/estimate_cost.py`)
The full film is 900 s on screen. Retakes are normal, so the estimate assumes **2.5 generations per shot on average**.

| Service | $/s | One take of all 90 | Expected (2.5 takes) |
|---|---|---|---|
| **Kling 3.0 Omni ref-to-video, 1080p** ★ | ~$0.224 | ~$202 | **~$504** |
| Kling 3.0 standard, 720p (needs upscaling) | ~$0.084 | ~$76 | ~$189 |
| Veo 3.1 Fast, 1080p (8 s + extension) | ~$0.12 | ~$173 | ~$432 |
| Veo 3.1 Standard, 1080p | ~$0.40 | ~$576 | ~$1,440 |
| Runway Gen-4.5, 720p (needs upscaling) | ~$0.12 | ~$108 | ~$270 |

**Suggested first spend: a three-shot pilot** (001, 003 and 010 with Kling Omni, 2 takes each), costing about **$13–15**, plus a few cents for reference images. It proves character consistency and the hero redesign before committing to the full film.

### Other possible costs (also only with your approval)
| Item | Free route | Paid route (approximate) |
|---|---|---|
| **Reference images (6)** | Draw them, or use any image tool you already have | A few cents to a few dollars |
| **Voices (96 lines, about 510 words)** | Record family or friends; `CLAUDE.md` makes dialogue optional | A text-to-speech subscription such as ElevenLabs, typically a low monthly plan |
| **Sound effects** | CC0 libraries (Freesound CC0 filter, Sonniss GDC bundles) | An AI SFX generator |
| **Music (12 cues, 15 min)** | A composer friend, or royalty-free library music with a licence that covers your use | An AI music service on a plan whose licence allows your use, or a commissioned composer |

## What I need from you before any generation
1. **Your choice of service**: Kling 3.0 (recommended), Veo 3.1 Fast, or another tool you already pay for.
2. **An API key for it.** It is saved through the secure environment credential form and never pasted into chat.
3. **Approval of a budget cap**, for example "pilot only, $15", then "full run, up to $550".
4. **Approval or changes to the Rigger** (the original hero redesign) and the proposed dialogue.

Once you approve, I'll write the service adapter against that provider's current API documentation, run the pilot, review the clips with you, and only then continue.

## Sources
- [Kling AI pricing breakdown (DEV Community)](https://dev.to/evan-dong/kling-ai-video-generation-pricing-complete-cost-breakdown-for-developers-2026-3fnp), [Kling 3 API pricing guide (EvoLink)](https://evolink.ai/blog/kling-3-api-pricing-integration-guide), [Kling 3.0 pricing tiers (MuAPI)](https://muapi.ai/kling-3-pricing), [Kling length limits (Atlas Cloud)](https://www.atlascloud.ai/blog/guides/kling-ai-video-length-limit)
- [Veo 3.1 API pricing (BenchLM)](https://benchlm.ai/media-pricing/veo), [Veo 3.1 Fast price cut (Skila)](https://dev.to/skilaai/google-just-made-ai-video-50-cheaper-openai-killed-sora-heres-the-new-pricing-math-1ag4)
- [Runway Gen-4.5 pricing (Magic Hour)](https://magichour.ai/blog/runway-gen-45-pricing), [Runway pricing 2026 (Creatify)](https://creatify.ai/blog/runway-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay)
- [Sora shutdown timeline (Zilliz)](https://zilliz.com/ai-faq/what-is-the-sora-shutdown-timeline), [OpenAI shuts down Sora (Engadget)](https://engadget.com/ai/openai-is-shutting-down-its-sora-video-generation-app-211023358.html), [Newsweek](https://newsweek.com/openai-scraps-sora-video-app-controversies-11731724)
