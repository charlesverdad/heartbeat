# Live subtitles design validation

Executed/reviewed: 2026-09-25. This report supports the revised
[design](design.md). It distinguishes observed results from simulations and
unverified deployment assumptions.

## Verdict

Proceed with a timing-first prototype. The independent caption path is sensible,
but the original claim that subtitles will follow YouTube playback through all
buffering/reconnect/DVR cases was too strong without a proven timeline mapping.
Neither this spike nor the public documentation proves that mapping for the
church's live stream.

The spike materially changes the design: explicit per-receiver calibration and
epochs; complete latency accounting; overlapping/stabilized ASR; separate language
completion; durable cue history with replay; and concrete production gates.

## Temporary artifacts and reproduction

Experiments and raw outputs are retained locally in:

```text
/private/tmp/live-subtitles-spike-20260924.FAZpFe/
  asr_probe.py            asr_results.json
  silence_result.json
  timing_probe.mjs        timing_results.json
  sse_probe.mjs           sse_results.json
  player_probe.html      README.md
```

The folder name reflects the initial work date; execution completed September 25.
The scripts are disposable spike code, not production modules. This report keeps
the important evidence after temporary storage is removed. No production stream,
cloud translator, or remote account was changed.

From that folder:

```sh
node timing_probe.mjs
node --experimental-eventsource sse_probe.mjs
/Users/charles/work/heartbeat/venv/bin/python asr_probe.py
```

The first two scripts use Node built-ins. The ASR script uses already-installed
packages, a cached model, and an existing local WAV. No packages/models were
installed or downloaded and the audio was not uploaded.

## Experiment 1: local sermon ASR and chunk sizes

**Executed inference, not simulation.** Environment: Apple M4 Max, macOS 26.5.1
arm64, PyTorch 2.10.0, `openai-whisper` 20250625, multilingual Whisper `base`, CPU,
four Torch threads, English transcription, FP32, greedy/temperature 0,
`condition_on_previous_text=False`. Model load took 0.333 seconds. One five-second
warm-up was excluded from the timings below.

Fixture: seconds 300–360 of
`youtube/work/mjHAolwGpoA/sermon16k.wav`, mono PCM16 at 16 kHz. The adjacent existing
ASR file records an original-media offset of 1396 seconds. Each sweep transcribed
the same 60 seconds as independent non-overlapping hard cuts, without VAD or
previous text. These are offline inference durations; collection/wait time is
**not** included.

| Cut length | Calls | Total inference | Median call | Observed p95 call | Inference/audio ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2 s | 30 | 3.619 s | 0.120 s | 0.1371 s | 0.060 |
| 5 s | 12 | 1.865 s | 0.159 s | 0.1906 s | 0.031 |
| 10 s | 6 | 1.365 s | 0.227 s | 0.2551 s | 0.023 |
| 30 s | 2 | 1.248 s | 0.624 s | 0.6617 s | 0.021 |

P95 is nearest-rank over a very small sample; for the larger cuts it is simply
the largest call. It is not a service-level latency estimate.

Observed text differences:

- Two-second cuts emitted fragments including “right but cannot inc-” and
  “you need to go. Go and buy this book.” The cut boundary itself can damage text.
- The 30-second output retained “committed member or serious about this community”
  where shorter cuts lost or distorted the phrase.
- Ten-second output also contained an apparently substituted phrase relative to
  the existing offline transcript. More context is not a guarantee of correctness.
- A separate five-second zero-audio input emitted an empty string in 0.100 seconds.
  This one case does not validate music/noise handling or hallucination suppression.

There was no manually verified ground truth. The adjacent ASR transcript is only
a comparison aid, so no WER, accuracy percentage, or model-quality ranking is
reported. The experiment supports testing larger overlapping ASR windows with
smaller stable output cues, not selecting `base` or estimating RX 9070 performance.
It also demonstrates why aggregate inference speed is not end-to-end caption delay.

Hashes for identifying the exact inputs:

```text
base.pt SHA-256:
ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e
60-second PCM fixture SHA-256:
5c5f75571c2dcbef84a4994636d1d4e8e5fe7b085efd0a4a76957900993304ef
```

## Experiment 2: clock, scheduling, deadline, and overload contracts

**Deterministic simulation.** All 16 checks passed. The script models our proposed
contract; it does not test a real YouTube player or its undocumented behavior.

Checks cover different source/player origins, half-open cue boundaries, silence,
pause, buffering, rewind, live jumps, late delivery, duplicate/out-of-order
revisions, wrong session/capture epoch, map invalidation, independent languages,
invalid player values/states, invalid intervals, clock drift, sample-clock
independence from wall-clock steps, prefix agreement, and serial overload.

Counterexamples that changed the design:

| Input assumption | Result | Consequence |
| --- | --- | --- |
| Source marker 100 s corresponds to player 73 s | Direct lookup uses the wrong timeline; calibrated offset is -27 s | Establish content alignment before rendering |
| Caption queue deletes played cues | Rewind cannot recover old text | Keep/query history by time |
| Five-second chunk plus 0.5 s stability + 1 s ASR + 1.5 s translation + 0.2 s transport | 8.2 s before delivery, even without backlog | Eight-second video delay is insufficient; with 0.5 s reserve the margin is -0.7 s |
| Sample clock differs by 100 ppm | 1.08 s error after three hours | Measure drift and verify anchors throughout a service |
| 120 arrivals every 2 s, each requiring 3 s of serial processing | Last item's queue wait is 119 s | Bound work age and shed expired work |
| Language completions take 0.8, 1.2, and 6 s | An all-results barrier delays the fastest language another 5.2 s | Deliver language results independently |

All timing inputs in this experiment were deliberately injected. They are not
measured YouTube delays, provider response times, or church clock drift. The
prefix-agreement example tests a basic contract, not a production streaming ASR
implementation or its correctness on sermon speech.

## Experiment 3: real HTTP/SSE reconnect and replay

**Executed loopback network test.** Node v25.9.0, built-in HTTP server, native
experimental EventSource client. No external dependencies.

Sequence observed:

1. Snapshot contained state through event sequence 2.
2. Event 3 was committed after snapshot capture, before subscription.
3. The subscriber requested `after=2` and received event 3.
4. The server closed the response and committed event 4 while disconnected.
5. EventSource automatically reconnected with `Last-Event-ID: 3`.
6. The client received event 4; collected IDs were exactly `[3, 4]` and the updated
   cue converged to revision 2.
7. A deliberately expired cursor received explicit `event: reset` framing.

All assertions passed. This validates a minimal transport/replay mechanism and
shows why the snapshot watermark matters. It does not validate browser behavior,
TLS/authentication, a reverse proxy, multi-client scale, crash-safe storage, or
atomic state/cursor persistence. Those remain implementation and deployment tests.

SSE was chosen for the pilot because viewer traffic is one-way and it supplies a
standard reconnect cursor mechanism. This is a simplicity decision, not a
throughput result or proof that WebSocket cannot work.

## Experiment 4: live-player field probe

**Prepared and JavaScript syntax-checked; not executed against YouTube.**
`player_probe.html` loads the official IFrame API and records player position,
duration, state, UTC/monotonic timestamps, manually entered source anchors, errors,
and autoplay-blocked events. It has a separate caption region and a container
fullscreen button, with downloadable JSON observations.

The browser connector reported no available browser. Inventory showed Chrome,
but native app access returned “Computer Use permissions are not granted.” No
live YouTube/browser timing or visual result is claimed. No church sender or
RX 9070 machine was connected for testing either.

To use on the receiving machine, serve the temporary folder over local HTTP:

```sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory .
```

Open `http://127.0.0.1:8766/player_probe.html`, enter the church test video's ID,
and follow the calibration/measurement procedure in the design. Production uses
HTTPS; this loopback page is only a diagnostic. Repeat observations at live edge,
after pause/buffering/DVR, refresh, stream restart, and over a full service.

## Research that informed the changes

Only primary project/vendor documentation was used for technical conclusions.
Links were checked during this review; dynamic compatibility tables must be
rechecked when choosing deployment versions.

| Question | Evidence | Design consequence |
| --- | --- | --- |
| Does playback time establish source time? | [YouTube IFrame API](https://developers.google.com/youtube/iframe_api_reference) exposes position/state and describes live duration, without our external audio-clock mapping | Treat calibration as a gate; public docs alone cannot prove continuity across resets |
| Can broadcast start metadata anchor audio? | [LiveBroadcasts resource](https://developers.google.com/youtube/v3/live/docs/liveBroadcasts) defines broadcast start and caption configuration | Metadata is not an observed correspondence between captured samples and played content |
| Is a minimum processing delay guaranteed? | [YouTube latency guidance](https://support.google.com/youtube/answer/7444635?hl=en) gives typical upper ranges for lower-latency modes | Measure actual headroom; include speech collection and tails |
| Can captions overlay the iframe? | [Embedded-player requirements](https://developers.google.com/youtube/terms/required-minimum-functionality) restrict overlays and require Referer identification | Separate region; valid embedding origin/referrer; no assumed OBS workaround |
| Will a native player fullscreen include external captions? | [Player parameters](https://developers.google.com/youtube/player_parameters) document embedded-player controls | Use a page-container fullscreen control and test it; page behavior remains an engineering inference awaiting browser QA |
| What does DVR imply? | [YouTube DVR guidance](https://support.google.com/youtube/answer/9296823?hl=en) supports pause/rewind with limits | Retain caption history and mappings for the supported viewing interval |
| Does an AMD path exist? | [whisper.cpp](https://github.com/ggml-org/whisper.cpp) documents Vulkan/HIP; [AMD Radeon matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html) lists RX 9070 in its 7.2.1 table and refers newer releases elsewhere | Candidate support is credible; actual OS/runtime/driver and stability remain untested |
| Can CUDA benchmarks be reused for Radeon? | [faster-whisper requirements](https://github.com/SYSTRAN/faster-whisper) specify NVIDIA GPU libraries | No assumption of stock AMD acceleration |
| Is fixed-window streaming enough? | [Whisper-Streaming](https://github.com/ufal/whisper_streaming) describes stable-prefix agreement and rolling buffers | Separate decoding, committing, and cue creation |
| Does SSE handle replay automatically? | [WHATWG EventSource specification](https://html.spec.whatwg.org/multipage/server-sent-events.html) specifies reconnection and last-event IDs | Implement durable history, snapshots, reset, and deduplication in the application |
| Is native live caption ingestion possible without re-encoding? | [YouTube live caption requirements](https://support.google.com/youtube/answer/3068031?hl=en) describe HTTP ingestion and caption-feed limits | Keep it as a single-language alternative; do not claim it requires video burn-in or assume arbitrary multilingual live tracks |

The AMD legacy matrix is evidence of a supported hardware path, not a recommendation
to install ROCm 7.2.1. Newer unified matrix pages were not successfully retrievable
through the research tool during this session; the design deliberately does not
assert a latest working release.

## Remaining validation gates

| Gate | Required evidence before production |
| --- | --- |
| Live timeline | Matching source/player markers and residual errors across normal playback, DVR, buffering, refresh, and stream/capture interruption on each receiving setup |
| Actual processing budget | Per-cue arrival lead, late/missing fraction, and critical-path stage timings under church latency settings and peak language load |
| RX 9070 | Exact OS/driver/runtime/model, rolling-ASR load, memory, full-service soak, worker recovery, and PC-off isolation test |
| Speech quality | Human reference samples and review covering sermon vocabulary, negation, scripture, accents, silence/music, and interpreter speech |
| Translation | Real selected-provider/model trials and bilingual review in each enabled language; no API/model comparison was executed in this spike |
| Browser/projector | Embed authorization/referrer, user play, page fullscreen, font/RTL readability, background recovery, and actual ad/interruption behavior |
| Deployment reliability | Proxy streaming/timeouts, publisher authentication, durable replay after hub crash, retention/DVR boundaries, and loss/overload recovery |

These are specific gaps in evidence, not completed tests. The revised design gives
acceptance targets and a staged rehearsal plan; successful local experiments do
not waive the live synchronization gate.
