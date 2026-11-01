# Live Multilingual Subtitles for Church Livestream

Design reviewed 2026-09-25. Evidence and reproduction details are in
[validation.md](validation.md).

## 1. Decision and validation status

Keep the **ATEM → YouTube → receiving browser** video path independent of
caption generation. Generate speech recognition and translations at the sending
location, deliver timestamped text through a separate service, and render it
below the embedded player.

This is a **feasible prototype architecture, conditional on an on-site timing
rehearsal**, not yet a validated production system. Research and a temporary
spike support the transport and scheduling approach. Actual YouTube timeline
alignment, church network latency, RX 9070 stability, and translation quality
remain deployment gates.

The original design needed four material changes:

- `getCurrentTime()` is useful only **after source-to-player calibration**. It
  does not establish that both clocks share an origin.
- Processing headroom includes collecting the speech chunk, stabilizing ASR,
  inference, translation, queueing, and delivery. YouTube latency is not a
  guaranteed minimum buffer.
- ASR decoding windows, stable transcript commits, and display cues are different
  things. Independently transcribing two-second cuts damaged text in the spike.
- Caption history, replay, session identity, revisions, and failure isolation are
  required in the first prototype. They cannot be deferred while claiming DVR
  or reconnect support.

## 2. Requirements and scope

The sending location has an ATEM Mini Pro-class switcher, an existing service
mix, and a caption PC with an AMD Radeon RX 9070 that has occasionally crashed.
The exact ATEM model, caption PC OS/driver, audio routing, YouTube latency/DVR
settings, embedding permissions, and receiving browser must be inventoried.

The initial pilot is English speech to Simplified Chinese (`zh-Hans`), with
English available explicitly as a fallback. Korean (`ko`) and Farsi (`fa`) use
the same architecture after language review. Spoken sermon/announcements are
in scope; reliable lyric transcription, overlapping speakers, automatic language
switching, and automatic Bible quotation replacement are not pilot commitments.

Required behavior:

- No caption process controls the ATEM encoder or sits between it and YouTube.
- Failure or shutdown of the caption PC leaves normal livestream playback usable.
- Captions follow calibrated playback, including supported pause and DVR use.
- Each receiving location chooses its language independently.
- Volunteers get language, captions on/off, size, projector fullscreen, and a
  clear captions/synchronization status. Calibration belongs in an operator panel.
- The normal YouTube watch link is always available as a video-only fallback.

## 3. Architecture and audio capture

```text
Service program audio ─────► ATEM ─────► YouTube ─────► embedded player
          │                                                │
          └► independent audio input                       │
                 │                                         │
                 ▼                                         │
          capture + sample clock                           │
                 │                                         │
          streaming ASR worker                             │
                 │                                         │
          committed source cues                            │
                 │                                         │
          translation workers                              │
                 │                                         │
          outbound HTTPS publish                           │
                 ▼                                         │
          caption hub + durable history ─► SSE ─► calibrated scheduler
                                                          │
                                                          ▼
                                              separate subtitle region
```

Use a spare mixer program output or independently tested audio tap. It must
contain the same microphones, playback, and mute decisions heard in the stream,
not merely the room/house mix. Account for any ATEM audio delay during calibration.
Do not make the caption PC an audio bridge or require its USB connection for the
ATEM to keep streaming. Test this physically by turning the caption PC off.

Capture continuously, including silence. Timestamp audio from the device sample
position and preserve its relationship to the ASR input after resampling to
16 kHz mono. Verify channel selection/downmixing, clipping, and phase cancellation.
VAD must not concatenate speech and thereby remove gaps from the timeline.
Capture overruns, missing samples, device reconnection, and clock discontinuities
must be detected and recorded, not silently compressed away.

Run capture/supervision separately from GPU inference. Use bounded queues and a
watchdog so a hung inference worker cannot block capture. A GPU driver failure
can still take down the entire PC; only the separate physical video path gives
protection against that failure. Shared power, mixer, and network remain shared
dependencies. Limit caption upload/retry traffic so it cannot congest the stream.

## 4. Three clocks and explicit alignment

Define the clocks before implementing a scheduler:

| Clock | Meaning | Use |
| --- | --- | --- |
| Source `s` | Seconds from captured sample positions within a capture epoch | Cue start/end and ASR window offsets |
| Player `p` | `getCurrentTime()` reported by this receiver's player | Presentation lookup |
| Wall/monotonic time | UTC for correlation; monotonic time for elapsed work | Diagnostics, deadlines, heartbeats |

The [IFrame API](https://developers.google.com/youtube/iframe_api_reference)
provides playback position and player state. Its live `getDuration()` describes
elapsed streaming time, which can include pre-event streaming and interruptions.
The documented API does not establish a mapping to our audio capture clock.

For each verified source/player epoch, model the relationship as:

```text
p = a × s + b
s_playing = (p - b) / a
show cue when cue.start_s <= s_playing < cue.end_s
```

Start with `a = 1`; obtain `b` by observing the **same content marker** in source
audio and YouTube playback. The offset absorbs different start times and fixed
audio-path delays. It is not the viewer's current network latency. Buffering
changes when a position is reached; it does not itself justify changing `b`.

Do not infer `b` from starting both programs together, subtracting wall clocks,
`getDuration() - getCurrentTime()`, or the broadcast's scheduled/actual start.
The [broadcast resource](https://developers.google.com/youtube/v3/live/docs/liveBroadcasts)
reports broadcast metadata, not an audio-sample anchor. Clock synchronization
helps measure latency but does not prove content alignment.

### Pilot calibration procedure

1. Start capture and normal streaming before the service. Create a session tied
   to the actual YouTube video ID and a unique capture epoch.
2. Record the source sample time of an identifiable spoken phrase/onset. During
   rehearsal, a distinctive counted phrase is useful; normal program speech can
   be used without adding anything to the production stream.
3. At each receiver, identify that same onset and record player time. With DVR,
   replay/pause around the onset to improve precision. Calculate `b = p - s`.
4. Verify against at least two more markers spanning a minute. Record residual
   error and operator uncertainty. Enable captions only after this check passes.
5. Check a marker every 15 minutes initially, and after receiver reload,
   player recreation, capture discontinuity, or stream interruption.

Keep calibration local to the receiver/player instance until tests demonstrate
that it can safely be shared. A refresh must revalidate it. Store anchor pairs,
video ID, capture epoch, player epoch, mapping revision, and verified ranges.
Retain earlier mappings for historical playback; do not apply a new mapping
across an unverified discontinuity.

A fixed offset may drift: the spike's assumed 100 ppm clock difference creates
1.08 seconds of error in three hours. This is an illustration, not a measurement
of the church's equipment. Fit a rate `a` only from sufficiently separated,
consistent anchors; noisy manual markers must not create aggressive corrections.

A large unexplained player jump can mean a seek or a timeline reset. The public
API does not give us a reliable content-identity proof for every case. Tested
DVR seeks within a verified mapping can use that mapping; ambiguous jumps,
rejoins, and resets hide captions until alignment is checked. Automatic audio
fingerprinting is a separate research option, requiring access to the receiving
audio; it is not available just by reading the cross-origin iframe.

## 5. Latency budget and overload policy

For a cue starting at source time `s0`, the subtitle must reach the receiver
before playback reaches the mapped start. Its critical-path generation delay is:

```text
G = speech collection + ASR stabilization/lookahead + remaining ASR work
    + translation + queue waits + delivery
headroom = source-to-viewer video delay - G - safety margin
```

Instrument actual stage timestamps to avoid double-counting concurrent work.
Fast inference alone is insufficient. Full-cue text cannot be finalized before
enough of that cue has been spoken.

The spike used these **illustrative inputs**, not measured service latencies:
0.5 s stabilization, 1.0 s ASR, 1.5 s translation, 0.2 s delivery, no queue wait,
and 0.5 s safety margin.

| Video delay | 2 s speech chunk: remaining headroom | 5 s speech chunk: remaining headroom |
| --- | ---: | ---: |
| 3 s | -2.7 s | -5.7 s |
| 5 s | -0.7 s | -3.7 s |
| 8 s | 2.3 s | -0.7 s |
| 12 s | 6.3 s | 3.3 s |

[YouTube's latency guidance](https://support.google.com/youtube/answer/7444635?hl=en)
describes most low-latency viewers as below ten seconds and ultra-low-latency
viewers as below five seconds. Those are not minimums or processing guarantees.
Normal latency is the first rehearsal candidate if the church accepts its delay;
measure the existing configuration before deciding to change it.

Measure generation delay and receiver lead time per cue/language, especially at
the live edge. Report percentiles and the late/missing fraction, not just averages.
A conservative planning check is `G_p95 + margin < video_delay_p05`; actual
per-cue arrival-before-playback measurements are the acceptance test. Clock error
must be bounded for any cross-machine latency statistic.

If headroom is insufficient, reduce stabilization/chunk latency without losing
accuracy, select a faster model/provider, reduce the active language set, or use
a rehearsed higher-latency setting. An operator may deliberately watch behind the
live edge with DVR, but this is an explicit viewing choice that must be measured;
do not automatically pause or seek video to wait for captions.

Queues must have both size and age limits. Drop/cancel work that cannot meet the
configured live deadline rather than continually getting further behind. Preserve
gap metadata and measure missing captions so shedding does not make latency
statistics look artificially good. A separate backfill job may populate history;
it must not compete with current live work. The overload simulation accumulated
119 seconds of wait after 120 chunks when 2-second arrivals needed 3 seconds of
serial work each.

## 6. ASR, stabilization, and segmentation

Treat these as separate stages:

1. **Decoding window:** bounded rolling audio with overlap and preceding context.
2. **Commit policy:** publish only transcript words that are stable enough to use.
3. **Translation/display cue:** divide committed speech at useful linguistic
   boundaries while retaining source start/end times.

A 2–5 second cue is a starting target, not an instruction to cut independent
2–5 second files for Whisper. In the local 60-second sermon experiment, two-second
cuts produced broken words and phrases; longer windows recovered some context.
No human reference was available, so the experiment does not establish WER or a
production model choice.

Use speech detection plus overlapping decoding and timestamp-aware deduplication.
Compare successive hypotheses; commit agreed prefixes or a finalized endpoint,
with a bounded hold time. [Whisper-Streaming](https://github.com/ufal/whisper_streaming)
describes local agreement and handling repeated/inaccurate boundaries; its current
README also points to SimulStreaming as its successor. Borrow the stabilization
contract, not an assumption that either project's backend supports this GPU.

Initial tuning candidates for rehearsal:

- Decode from a rolling context window; benchmark its repeated computation cost.
- Commit stable speech into roughly 2–5 second cues, preferring pauses or clause
  boundaries. Start testing an approximately 0.5-second endpoint pause.
- Use a configurable maximum hold, initially 6 seconds. If no stable usable
  prefix exists at the deadline, record a gap; do not publish guessed text.
- Keep overlap/context internally, but never emit the same words twice.
- Use source timestamps, not inference completion times. Whisper word boundaries
  are estimates and need validation against the audio.
- Require actual speech evidence. Test silence, music, applause, repeated phrases,
  accents, quiet speech, and interpreter transitions. One zero-audio test returning
  empty text does not prove hallucination suppression.

Committed source cues are immutable in the live pipeline. Corrections require a
new source revision and matching regenerated translations; do not attach an old
translation to corrected text. Prefer to keep already displayed text stable.

## 7. Runtime choice and RX 9070 qualification

The first **candidate**, not a qualified selection, is `whisper.cpp` with Vulkan,
plus a smaller CPU model as a separately benchmarked fallback. Its
[upstream documentation](https://github.com/ggml-org/whisper.cpp) describes Vulkan,
HIP/ROCm, CPU inference, and a basic microphone streaming example. That example
is not a complete stable-cue pipeline.

Compare Vulkan and HIP/ROCm on the actual PC. AMD's
[Radeon Linux compatibility matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html)
explicitly includes RX 9070 in its documented 7.2.1 matrix; that page now points
to unified documentation for newer releases. This is support evidence, not an
instruction to install an old release. Select a current supported combination of
GPU, OS, driver, runtime, and inference framework and pin the working versions.
Check the separate Windows requirements if applicable.

Do not choose `faster-whisper` for AMD acceleration based on its CUDA benchmarks:
its [documented GPU setup](https://github.com/SYSTRAN/faster-whisper) requires
NVIDIA CUDA/cuDNN. CPU use or an explicitly tested alternative build is a separate
choice. DirectML is not an interchangeable switch for these runtimes.

Benchmark realistic rolling windows, stabilization, warm-up, and concurrent
translation. Measure peak memory, queue age, service-time percentiles, and
accuracy during a full-service soak. Start with ASR alone on the GPU; an API
translator avoids immediately making ASR and an LLM compete for GPU resources.
A local translator remains an option if it meets the same quality and load tests.

The spike ran cached Whisper `base` on an Apple M4 Max CPU only. It cannot predict
RX 9070 throughput, driver stability, a larger model's accuracy, or recovery from
GPU failure. Cloud fallback is an operational option only after its provider,
credentials, audio handling, cost, and deadlines are configured and rehearsed.

## 8. Translation and language review

Initially translate one language per bounded job. Publish each language as it
becomes ready; a slow or failed Farsi translation must not hold Chinese captions.
Per-language queues should preserve source order/context with bounded concurrency.
A multi-language call may be evaluated later, but do not wait for a combined
result merely for transport convenience. The spike demonstrated this coupling
with injected timings; it did not benchmark a translation model.

Each request contains the current committed source cue, previous 1–3 source
cues as context, source/target language, a small approved glossary, and cue ID /
source revision. Return only the current cue's translation in validated structured
output. Validate identity, language field, nonempty text, length, and revision.
Treat sermon text as data, including speech that resembles model instructions.
Timeouts, malformed output, and stale responses become explicit language states.
Retries are bounded by the cue's deadline.

Preserve negation, names, numbers, theological meaning, and quoted versus
paraphrased speech. Do not summarize or add interpretation to fit the screen.
Use prior context without repeating it. If translated text needs multiple display
cues, retain the whole translation and assign reasonable intervals within the
source span; validate reading speed and line breaking with native readers.
Do not divide target words mechanically by source word timestamps.

The existing [glossary](../glossary.json) is mainly English ASR correction data,
not an approved multilingual terminology table. Reuse it cautiously and add
reviewed mappings for each language. Do not blindly replace ordinary uses of
“heartbeat” or “grace” with church-specific meanings. Scripture substitution is
deferred: an inferred reference must not silently replace what the speaker said.

Before adding a language, compare candidate translators on the same sermon
samples, including interrupted clauses, negation, scripture, names, and code
switching. Measure latency/cost and get a bilingual reviewer to assess meaning
and readability. No translator or quality winner was established in this spike.

## 9. Caption and session contract

Use explicit versioned messages. For example, a full cue snapshot after one
language has completed:

```json
{
  "schema_version": 1,
  "session_id": "service-2026-09-27-unique-id",
  "video_id": "EXAMPLE1234",
  "capture_epoch": "capture-unique-id",
  "event_seq": 1842,
  "cue_id": "cue-317",
  "revision": 2,
  "source_revision": 1,
  "start_s": 173.4,
  "end_s": 177.8,
  "source": {"language": "en", "text": "We receive grace rather than earn it."},
  "translations": {
    "zh-Hans": {"status": "ready", "source_revision": 1, "text": "我们领受恩典，而不是赚取恩典。"},
    "ko": {"status": "pending", "source_revision": 1},
    "fa": {"status": "failed", "source_revision": 1}
  }
}
```

The example translation is illustrative, not reviewed terminology.

- `session_id` identifies the service; a video ID alone is insufficient for resets.
- `capture_epoch` changes when capture continuity is lost. ASR worker restart alone
  need not change it if capture and its sample clock continued.
- Cue identity and `[start_s, end_s)` refer to source audio within that epoch.
- `revision` increases when the hub merges an accepted cue update. Older or
  duplicate snapshots cannot overwrite newer state. Workers must not independently
  replace the whole translations map and lose another language's result.
- `event_seq` is the hub's durable ordering/replay cursor, including translation
  updates. It is not the cue ID. Reject stale source revisions before merging.
- Session metadata carries languages, video ID, retention bounds, capture epochs,
  status, and a snapshot cursor. Receiver calibration is stored separately.

Validate finite ordered times, text size, supported languages, session ownership,
and revisions at ingestion. Reject overlapping committed cues unless an explicit
multi-speaker policy exists. Log producer idempotency keys and acknowledgements
so retries after a network failure do not create duplicate cues.

## 10. Delivery, replay, and retention

Use **HTTPS POST from sender to hub, HTTP snapshot/history plus SSE to receivers**
for the pilot. No inbound connection to the church PC is required. The viewer
needs a one-way event stream; control requests can use ordinary HTTP.

[SSE/EventSource](https://html.spec.whatwg.org/multipage/server-sent-events.html)
defines reconnection and `Last-Event-ID`. It does not provide storage or replay
by itself. WebSocket is also viable, but requires an application reconnect/replay
protocol; there is no demonstrated need for bidirectional streaming here.

The local experiment verified actual HTTP streaming, automatic EventSource
reconnection, replay, and a snapshot/subscription race. It used Node's experimental
EventSource implementation, not the production browser or hosting proxy.

Required protocol:

1. Fetch a consistent session/cue snapshot and its `through_seq` cursor.
2. Subscribe to events after that cursor. Events committed between snapshot and
   subscription are included in replay; then follow live events without a gap.
3. Use the last applied event cursor to resume. A fresh page or new EventSource
   instance must bootstrap explicitly; in-memory automatic reconnect is not
   durable client state.
4. Apply revisions idempotently. Persist cursor and corresponding state together,
   or discard both and resnapshot after a crash. Do not persist only the cursor.
5. If replay has expired or session identity changed, send an explicit reset;
   close the old subscription, obtain a snapshot, and resume from its watermark.
6. Publish heartbeats and session/capture status. Set heartbeat/proxy timeouts,
   disable response buffering, and bound each client's output queue. Disconnect
   slow clients and let replay recover them rather than blocking the producer.

The hub atomically persists cue state plus event log before acknowledging writes.
A single instance with SQLite is sufficient for an initial small deployment;
restarts must preserve event sequencing. Managed pub/sub alone is not history.
Use TLS and authenticated publisher/operator endpoints, keep provider keys off
receivers, and make receiver authorization match the intended audience. Render
caption strings as text, never HTML. For restricted viewers, prefer same-origin
session-cookie authentication: native EventSource does not offer arbitrary request
headers. Do not put long-lived bearer credentials in the stream URL.

Retain cue snapshots and epoch mappings for the **entire pilot service**, with a
configured four-hour pilot maximum and at least 24-hour server retention after
it ends. Event replay may have a shorter, explicit window because snapshots can
recover it. DVR needs cue history, not just unacknowledged transport messages.
Bound receiver memory; fetch missing historical ranges or clearly show that
captions are unavailable for that position. Extend retention before longer events.
YouTube's own [DVR limits](https://support.google.com/youtube/answer/9296823?hl=en)
are separate from our caption retention.

## 11. Receiver scheduling and presentation

Keep cues indexed by source time/epoch. Do not destructively pop a live FIFO;
rewinding must be able to find old cues. Poll playback around every 200 ms and
resample immediately after relevant player/visibility events. Polling rate is a
starting setting, not a guarantee against background-tab throttling.

| Situation | Caption behavior |
| --- | --- |
| Playing with verified mapping | Look up the cue at mapped player position |
| Paused/buffering with unchanged position | Keep the matching cue; do not advance by wall time |
| Silence or no matching cue | Clear text |
| Seek/live return within verified timeline | Look up destination; skip intervening cues |
| Late translation within its cue | Show only if useful reading time remains; count as late |
| Translation arriving after cue end | Retain for history; never flash it over later speech |
| Missing/failed selected language | Clear text or use explicitly selected English fallback |
| Invalid position, stopped/error player, unknown mapping | Hide captions and show status outside player |
| Caption transport disconnected | Continue valid cached cues; reconnect; clear when none match |
| Source restart or ambiguous player reset | Require a matching epoch/verified mapping before display |

Do not repeatedly replace a cue's visible translation once it has started showing.
A new language selection may render that cue in the selected language. Status
messages distinguish unavailable captions from ordinary silence without exposing
AI tooling to volunteers.

Keep captions **below** the player in a separate region. YouTube's
[embedded-player requirements](https://developers.google.com/youtube/terms/required-minimum-functionality)
prohibit obscuring the player with overlays and require client identification via
HTTP Referer. Serve the receiver over HTTPS with an appropriate referrer policy;
do not run it as a `file://` page. Include the documented `origin` parameter.
Keep controls and branding accessible and respect player minimum dimensions.

Fullscreen the page container holding **both** the iframe and subtitle region.
The player's own fullscreen control can show only the video, losing the external
captions; explain the page's “Projector fullscreen” control and test it on the
actual browser/projector. Handle blocked autoplay with a normal user play action.
Use `lang`, Farsi RTL direction/bidi isolation, and fonts supporting all scripts;
verify size/line wrapping from the back of the room.

Ads, redirects, and platform interruptions can invalidate assumptions about what
content is visible. The public IFrame API is not a reliable ad-status/content
identity interface. Rehearse the actual account/stream configuration and provide
an operator captions-off control. Do not suppress ads or claim automatic sync
through every interruption. OBS composition over an embedded YouTube player is
not an established workaround for its overlay requirements; it is outside this
design.

## 12. Reliability and operation

| Failure | Recovery |
| --- | --- |
| ASR worker hangs/crashes | Watchdog restarts worker; keep capture clock if valid; mark missing span |
| GPU driver/PC fails | Captions stop; ATEM/YouTube continue; restart creates/verifies capture epoch |
| Translation language fails | That language unavailable; others continue; bounded retries |
| Publisher network fails | Bounded local outbox; idempotent retry; stale work cannot starve live work |
| Hub restarts | Restore persisted session/cues/cursor; receivers replay or resnapshot |
| Receiver caption code fails | Leave player mounted; offer normal YouTube fallback |
| YouTube player fails or loses alignment | Hide captions; recover video separately; revalidate mapping |

CPU fallback cannot rescue a PC that has crashed. No fallback is considered
available until benchmarked and exercised. Stop generating rather than silently
accumulating an unusable backlog.

Sender workflow: start the existing stream, select its video ID and languages,
verify audio capture, warm models, and check a sample cue. Receiver workflow:
open the page, start playback, select language, verify/calibrate alignment, then
use projector fullscreen. Check alignment and status during the service. End the
caption session explicitly and retain its history according to policy.

Operator diagnostics should include audio level/dropouts, capture epoch, ASR
commit lag, oldest queue age, per-language completion/failure, sender/hub heartbeat,
receiver lead time, late/missing cue rate, and calibration age/error. Distinguish
an unaligned player, an unavailable language, and a quiet microphone.

## 13. Alternatives and when to revisit them

| Alternative | Assessment |
| --- | --- |
| Receiver-side ASR/translation | Avoids sender setup, but processing follows heard audio unless playback is deliberately delayed; fallback for separate use cases |
| YouTube native live captions | Worth a separate single-language trial: HTTP caption ingestion exists independently of video encoding; documented live caption feeds are limited, so it does not establish selectable Chinese/Korean/Farsi support |
| Embedded CEA-608/708 | Requires a supported encoder path and has YouTube track constraints; not a reason to risk the independent ATEM setup |
| Re-encode/burn captions into video | Adds a video dependency and prevents per-viewer language choice; outside current scope |
| Local audio fingerprint alignment | Potential automatic calibration if permitted receiving-audio access exists; unvalidated |
| WebSocket or managed realtime | Valid transport alternatives if hosting needs them; must preserve the same snapshot/replay/history contract |

YouTube documents both [live caption delivery options and track/feed limits](https://support.google.com/youtube/answer/3068031?hl=en).
Do not confuse those with uploading caption files for recorded videos via the
Data API, or assume native caption ingestion requires video re-encoding.

## 14. Prototype order and go/no-go criteria

1. **Prove timing first:** a receiver diagnostic page, manually timestamped known
   source phrases, a real test livestream, per-receiver calibration, pause/DVR,
   refresh, reconnect, and stream interruption. No ASR is needed to expose clock
   mapping failures. The temporary spike includes an unexecuted field probe.
2. **Add real ASR and one language:** rolling context/stability, immutable source
   cues, glossary, bounded translation, durable hub/SSE replay, and status. Replay
   representative sermon audio in real time before attaching live capture.
3. **Rehearse a whole service on target equipment:** observe drift and load;
   disconnect caption network, restart hub/worker, and turn off the caption PC.
4. **Expand languages only after review:** compare meaning/readability, deadlines,
   partial failure, GPU/API load, and cost for each additional language.

Proposed pilot acceptance targets, to be confirmed during rehearsal:

- Video continues throughout every caption-component failure injection.
- At least 95% of reviewed cue boundaries are within ±1 second of corresponding
  received speech, including tested pause/DVR/recovery scenarios.
- At least 95% of expected cues per enabled language arrive at least 0.5 seconds
  before their mapped start at normal viewing position. Report gaps, rejected
  outputs, and late drops in the denominator; also report worst lateness. Establish
  expected speech coverage from annotated rehearsal audio, not only the cues the
  ASR happened to emit.
- No sustained growth in queue age during a full service. Demonstrate recovery
  from caption-network loss without duplicate, stale, or wrong-session text.
- Representative bilingual review finds no critical changes to negation,
  scripture references, names, or theological meaning; remaining readability
  problems are resolved before congregation use.
- Volunteers can start playback, choose language, calibrate with the operator
  procedure, enter projector fullscreen, and restore video-only viewing.

A failed clock-mapping test is a stop condition for this custom-player approach;
revisit native caption ingestion or a player/transport with explicit media-clock
mapping. A failed latency budget requires a changed processing/viewing strategy.
Neither is fixed by selecting WebSocket or a faster polling interval.
