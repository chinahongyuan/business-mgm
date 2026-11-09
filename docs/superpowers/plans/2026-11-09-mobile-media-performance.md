# Mobile media performance implementation plan

> For agentic workers: use subagent-driven-development for the isolated backend task, with spec and code review. The user approved implementation on 2026-11-09. Preserve unrelated workspace changes.

**Goal:** Reduce image bytes and avoid unsolicited video downloads on the existing mobile product list and detail pages.

**Architecture:** Preserve original uploads and API fields. A filesystem media service generates immutable derived files and an atomic manifest, without schema changes or doing expensive processing on GET requests. Mobile clients consume optional media metadata with original-file fallback. Keep current API authentication, no-store policy, navigation, filters, review submission and view counting.

**Tech stack:** Flask, Pillow, FFmpeg, Vue 3, native picture/video, pytest, Playwright.

## Contract

`coverMedia` (optional/null) on list items and `detailMedia` (URL-keyed map) on product detail:

```ts
type MediaVariant = { url: string; width: number; height: number; bytes: number };
type MediaAsset = {
  original: string; width: number; height: number;
  images?: MediaVariant[]; // WebP, widths 320/640/720/1080, no upscaling
  poster?: string;
  videos?: (MediaVariant & { label: string })[]; // low/HD MP4, low first
};
```

Missing/failed/pending/animated files use the original; original images remain available in the lightbox. Video markup is inert until the user clicks; preserve existing source alternatives and playback controls. No artificial image assets, font downloads, animation libraries, CDN account changes, or full redesign.

## Tasks

- [x] Backend: write failing tests for resize/output bytes, originals unchanged, no upscale, animation fallback, URL/path confinement, corrupt/missing manifests, immutable caching and video Range. Implement `backend/app/services/media_assets.py` (split video worker as needed), integrate upload and mobile serializers, bounded background video processing, Pillow dependency, Docker FFmpeg, resumable CLI backfill and deployment instructions. Observe test failure then success.
- [x] Frontend: write browser tests proving no video requests before click (including nested source), first-image priority, image srcset and original preview. Implement `frontend-mobile/src/utils/media.ts`, responsive cover component, deferred detail-media helpers, and loading/error styles. Independently load detail and reviews/config; clean up on route changes, guard stale requests. Preserve image/video interactions and list state.
- [x] Integration: run existing session/upload/filter tests, type check and production build; run isolated browser fixture with real generated media (no production database), test mobile/desktop, cold/warm network, image fallback, review delay, video playback/switch/seek and navigation. Capture repeatable byte/timing evidence and screenshots. Review spec compliance then code quality; fix findings.
- [x] Delivery: record commands/results and explicit limits in `docs/mobile-media-performance.md`; package the mobile build used by Flask. No production deployment or original-file deletion.

## Acceptance

- Original files/URLs and animated media remain usable.
- List downloads appropriate responsive thumbnails; detail images below viewport are deferred, with dimensions reserved when known.
- Opening detail downloads no video body until an explicit play click; poster/low/HD variants available for processed videos.
- Failures show actionable retry; fallback never loops and no extra marketing copy is added.
- Media requests preserve Range semantics and updated media gets new URLs. APIs remain uncached.
- Developers and agents have one documented media contract, status manifests, resumable backfill and deterministic tests.
- Test network: 1 Mbps download, 300 ms latency, cold/warm profiles. Synthetic-fixture metrics must be labeled and not presented as production gains.
