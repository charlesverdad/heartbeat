# Live Multilingual Subtitles for Church Livestream

## 1. Overview

The church currently livestreams from the sending location to another church location using an ATEM Mini Pro-class Blackmagic switcher and YouTube Live.

The goal is to provide near-real-time translated subtitles at the receiving location without modifying or re-encoding the existing video stream.

The proposed solution is to transcribe and translate the service at the **sending location**, then send timestamped subtitle data independently of the YouTube stream. The receiving location uses a custom web frontend containing the YouTube player and a synchronized subtitle display.

A key advantage of this design is that YouTube's livestream latency can be used as processing headroom. The transcription and translation system can wait for meaningful speech chunks or complete sentences while the corresponding video is still travelling through YouTube's delivery pipeline.

---

# 2. Current Environment

## Sending location

Existing infrastructure:

- Blackmagic ATEM Mini Pro or similar ATEM Mini model with direct livestream capability.
- YouTube Live as the livestream transport.
- Desktop computer available for AI processing.
- AMD Radeon RX 9070 GPU.
- Existing audio source available from the service/mixer.

The ATEM and YouTube livestream should remain independent of the subtitle system.

If the subtitle PC or GPU crashes, the livestream must continue normally.

## Receiving location

The remote location currently watches the YouTube livestream.

The proposed system replaces the normal YouTube viewing page with a purpose-built web frontend containing:

- embedded YouTube Live player;
- translated subtitle display;
- language selector;
- fullscreen/projector mode.

---

# 3. Problem

The receiving congregation needs translated subtitles for the live service.

A straightforward approach would be:

1. receive the video stream;
2. transcribe the audio;
3. translate the transcript;
4. burn subtitles into the video;
5. re-encode/output the result.

This introduces several undesirable characteristics:

- additional video encode/decode stages;
- additional latency;
- significantly more processing;
- a new critical component in the video path;
- reduced reliability;
- difficulty supporting multiple languages;
- potential video quality degradation.

Performing transcription at the receiving location also means the subtitles inherently appear after additional transcription and translation latency.

For example:

```text
YouTube video arrives
        ↓
audio heard
        ↓
speech recognition
        ↓
translation
        ↓
subtitle displayed
```

Even a fast pipeline therefore causes the subtitle to trail the spoken audio.

---

# 4. Design Principle

Video and subtitles should be treated as **two independent synchronized streams**.

```text
VIDEO PATH

ATEM
  ↓
YouTube Live
  ↓
Receiving browser


CAPTION PATH

Mixer/audio
  ↓
Speech recognition
  ↓
Translation
  ↓
Timestamped caption messages
  ↓
Receiving browser
```

The video stream remains completely unchanged.

The receiving frontend combines the two at presentation time.

---

# 5. Proposed Architecture

## High-level architecture

```text
                         SENDING LOCATION

                    ┌─────────────────────┐
                    │ Service audio/mixer │
                    └──────────┬──────────┘
                               │
                   ┌───────────┴───────────┐
                   │                       │
                   ▼                       ▼

               ATEM Mini               Caption PC
                   │                       │
                   │                    Whisper
                   │                       │
                   │               transcript chunks
                   │                       │
                   │                  Translation
                   │                       │
                   │              multilingual captions
                   │                       │
                   │                  WebSocket/API
                   │                       │
                   ▼                       │
              YouTube Live                 │
                   │                       │
                   └───────────┬───────────┘
                               │
                               ▼

                        RECEIVING LOCATION

                    Custom livestream webpage

                ┌───────────────────────────┐
                │                           │
                │      YouTube player       │
                │                           │
                ├───────────────────────────┤
                │ translated subtitle text  │
                └───────────────────────────┘

                     Language: 中文 ▼
```

---

# 6. Source-Side Transcription

Speech recognition should run at the sending location.

The transcription system receives the same service audio that ultimately enters the livestream.

A likely implementation is Whisper or a Whisper-derived streaming implementation.

Possible runtime options include:

- whisper.cpp;
- another Whisper implementation with AMD/Vulkan/ROCm support;
- a cloud transcription API if local GPU reliability becomes a problem.

The Radeon RX 9070 should be treated as an accelerator, not as part of the critical livestream path.

If transcription crashes, the YouTube livestream continues unaffected.

---

# 7. Speech Chunking

Translation should not be performed word-by-word.

Machine translation generally benefits substantially from receiving enough context to understand the sentence structure, negation, terminology and intended meaning.

However, waiting indefinitely for grammatical sentence boundaries is unsuitable for live speech because speakers often produce long sentences.

The transcription system should therefore produce **stable semantic chunks**.

Suggested target:

- approximately 2–5 seconds of speech;
- approximately 8–20 words;
- preferably ending on a natural speech pause;
- shorter when a clear sentence boundary occurs.

Example source speech:

```text
"I think what Paul is telling us here /
is that salvation isn't something we earn /
but something God gives us through grace."
```

These can become three separate subtitle units while retaining enough context for good translation.

---

# 8. Translation

The stable transcript chunk is translated into all required target languages.

Example:

```text
English transcript
        │
        ├── Simplified Chinese
        ├── Korean
        ├── Farsi
        └── future languages
```

Translation may initially be implemented using:

- an LLM API;
- a local multilingual LLM;
- a dedicated translation model.

Because video delivery through YouTube introduces several seconds of latency, the translation pipeline does not have to optimize exclusively for minimum latency.

It can instead favour translation quality.

The translator should receive recent linguistic context.

For example:

```text
Previous transcript:
[previous 1–3 chunks]

Current chunk:
[chunk to translate]
```

Only the current chunk is emitted as the subtitle.

The previous text is context only.

---

# 9. Translation Prompting / Domain Context

Church services contain terminology for which generic translations may be inconsistent.

The system should support a domain glossary.

Examples:

```text
Heartbeat Church
Jesus Christ
Holy Spirit
grace
salvation
discipleship
Ephesians
1 Corinthians
Full Life in Christ
```

Translation instructions should prioritize:

- preserving theological meaning;
- avoiding summarization;
- avoiding additional interpretation;
- consistent terminology;
- natural subtitle-length target language;
- standard Christian vocabulary in the target language.

Future improvements may include using canonical Bible translations when scripture references or quotations are detected.

---

# 10. Multilingual Caption Message

Each subtitle event should contain one source segment and zero or more translations.

Conceptually:

```json
{
  "id": 1842,
  "start": 173.4,
  "end": 177.8,
  "source": "We receive grace rather than earn it.",
  "translations": {
    "zh-CN": "...",
    "ko": "...",
    "fa": "..."
  }
}
```

The exact schema is implementation-specific.

The important properties are:

- stable unique ID;
- source timing;
- original transcript;
- translations;
- ability to add new languages without modifying the video pipeline.

---

# 11. Timing Model

Timing is the critical part of the design.

The captions should be generated against the source audio timeline.

The receiving frontend should not simply display a subtitle when it arrives.

Instead:

```text
caption arrives
      ↓
place in queue
      ↓
compare caption timestamp with video playback position
      ↓
display when matching video reaches that position
```

This means the subtitle can arrive several seconds before the corresponding video.

---

# 12. Using YouTube Latency as Processing Headroom

The system intentionally takes advantage of livestream latency.

Example:

```text
T+0.0   Speaker begins sentence

T+2.5   enough context available
T+2.8   transcription finalized
T+3.2   translation completed
T+3.3   subtitle arrives at receiving browser

T+8.0   corresponding YouTube video/audio reaches viewer
```

In this example, the receiving browser has the translated subtitle approximately five seconds before it needs to display it.

This permits substantially better translation than a receiver-side transcription pipeline.

The exact available buffer depends on the configured YouTube livestream latency mode and real-world delivery latency.

The system must therefore not rely on a hardcoded assumption such as "YouTube is always eight seconds behind."

---

# 13. Synchronization

The receiving frontend should synchronize subtitles against the actual YouTube player position.

The YouTube IFrame Player API exposes the player's current playback position.

Conceptually:

```javascript
videoTime = player.getCurrentTime()
caption = captionTimeline.lookup(videoTime)
```

The subtitle scheduler can poll playback position several times per second.

Speech subtitles do not require frame-accurate synchronization.

This has several benefits.

If the YouTube player:

- buffers;
- pauses;
- falls behind;
- reconnects;
- rewinds using DVR;

the caption system follows the actual video playback rather than assuming fixed network latency.

---

# 14. Timeline Mapping

One implementation question requiring validation is how best to map source timestamps onto YouTube player timestamps during a live event.

Potential representations include:

### Stream-relative timestamp

```text
173.4 seconds since beginning of broadcast
```

### Absolute source timestamp

```text
2026-09-27T11:32:18.420+10:00
```

The system needs a reliable mapping between:

```text
source audio time
        ↕
YouTube playback position
```

This mapping could be established at session start and updated if required.

This should be specifically validated during implementation because YouTube live-player behaviour, DVR windows and player timing semantics may influence the best strategy.

---

# 15. Receiving Frontend

The receiving site should use a custom web application.

Example:

```text
Heartbeat Live

Language: [ 中文 ▼ ]

┌─────────────────────────────────────────┐
│                                         │
│              YouTube Live               │
│                                         │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│      我们得救是本乎恩典，也因着信。       │
└─────────────────────────────────────────┘

                    [ Fullscreen ]
```

Primary controls:

- language;
- captions on/off;
- font size;
- fullscreen.

Potential future controls:

- bilingual mode;
- font;
- number of subtitle lines;
- subtitle history;
- source transcript;
- accessibility options.

---

# 16. Subtitle Rendering

The technically easiest implementation is an absolutely positioned HTML element over the YouTube iframe.

However, YouTube's embedded-player requirements restrict placing overlays over the player.

Therefore the initial production design should place subtitles in a separate visual region immediately below the YouTube player.

Example:

```text
┌───────────────────────────────────────┐
│                                       │
│             YouTube video             │
│                                       │
├───────────────────────────────────────┤
│      translated subtitle region       │
└───────────────────────────────────────┘
```

For a projector this should still appear visually integrated.

If true on-video captions become necessary, a separate local compositor such as OBS can combine the webpage/video output with the caption layer for projection.

The actual YouTube stream still does not need to be modified.

---

# 17. Multiple Languages

The architecture naturally supports multiple languages.

The source transcript is generated once.

Translations are generated independently:

```text
                  ┌── zh-CN
                  │
English transcript├── ko
                  │
                  ├── fa
                  │
                  └── future languages
```

Every receiving location can watch exactly the same YouTube stream while selecting a different subtitle language.

Examples:

```text
/live?lang=zh-CN
/live?lang=fa
/live?lang=ko
```

Alternatively the user selects the language using the frontend.

Adding another language should require no changes to the video infrastructure.

---

# 18. Caption Transport

Caption messages can be delivered independently over normal internet infrastructure.

Likely choices:

- WebSocket;
- Server-Sent Events;
- realtime database/pub-sub service;
- polling HTTP endpoint.

WebSocket is the initial preferred model because:

- captions are small;
- updates are realtime;
- one source can fan out to many viewers;
- frontend implementation is simple.

Bandwidth requirements are negligible compared with the video stream.

---

# 19. Reliability

A major design requirement is that subtitles must never become a critical dependency for the livestream.

The architecture should degrade as:

```text
ATEM              working
YouTube           working
video             working

Caption PC        failed
GPU               failed
translation       failed
WebSocket         failed

Result:
video continues normally
captions disappear
```

This is preferable to a design where video is passed through a subtitle PC before reaching the audience.

Potential resilience improvements:

- CPU transcription fallback;
- smaller fallback ASR model;
- cloud transcription fallback;
- automatic reconnect for caption clients;
- WebSocket message replay;
- caption sequence numbers.

---

# 20. Radeon RX 9070

The sending PC contains an AMD Radeon RX 9070.

The GPU should be used for local inference where practical.

The implementation should favour runtimes with demonstrated AMD compatibility, potentially through:

- Vulkan;
- ROCm/HIP;
- DirectML where appropriate.

Because the machine has experienced occasional GPU crashes, the first implementation should not place any video processing dependency on this machine.

Only subtitle generation should use the GPU.

A GPU failure should not affect:

- ATEM switching;
- YouTube encoding;
- YouTube delivery;
- playback at the receiving location.

---

# 21. Operational Workflow

A target Sunday workflow should eventually be:

### Sending location

1. Start normal ATEM / YouTube livestream.
2. Open caption service.
3. Select target languages.
4. Start caption generation.

### Receiving location

1. Open Heartbeat livestream webpage.
2. Select language.
3. Enter fullscreen.
4. Project.

No AI tooling should need to be visible to volunteers.

---

# 22. Other Solutions Considered

The following alternatives were considered but are not currently preferred:

- receiver-side transcription and translation;
- re-ingesting and re-encoding the YouTube feed with burned-in subtitles;
- generating captions and injecting them directly into the outgoing broadcast;
- YouTube-native automatic or translated captions;
- audio fingerprint synchronization at the receiving location;
- subtitle generation followed by OBS composition;
- embedded broadcast closed-caption standards such as CEA-608/708;
- dedicated translation hardware/service.

Audio fingerprinting remains potentially useful as a future compatibility mechanism where the receiving subtitle device does not control the video player.

---

# 23. Why the Proposed Design Is Preferred

The proposed system has several important properties:

### Existing livestream remains unchanged

The ATEM → YouTube path remains the primary reliable transport.

### Better translation quality

The sender can wait for semantic chunks or complete thoughts before translating.

### YouTube latency becomes useful

The video delivery delay provides processing time before subtitles are required.

### Multiple languages are inexpensive

One transcript can feed many translations.

### No video re-encoding

Only lightweight text data is transmitted separately.

### Subtitle failure is non-critical

A subtitle system failure does not interrupt the service.

### Synchronization follows actual playback

The custom receiver frontend can synchronize against the YouTube player's real playback position rather than estimated network latency.

---

# 24. Questions Requiring Validation

Before implementation, the following assumptions should be technically validated.

1. **YouTube timeline mapping**
   - Determine the most reliable method for mapping source audio timestamps to live YouTube player playback time.
   - Test behaviour after buffering, reconnecting and DVR rewind.

2. **Available latency**
   - Measure actual source-to-receiver YouTube latency under the church's current stream settings.
   - Determine how much processing budget is consistently available.

3. **Whisper streaming implementation**
   - Validate the best local ASR runtime for RX 9070.
   - Measure transcription latency and accuracy during real sermons.

4. **AMD stability**
   - Determine whether Vulkan, ROCm or another inference backend is most reliable on the existing Radeon machine.

5. **Speech segmentation**
   - Experiment with stable semantic chunk sizes.
   - Balance translation context against subtitle responsiveness.

6. **Translation quality**
   - Compare an LLM against dedicated translation models for sermon speech.
   - Validate theological terminology in target languages.

7. **Multi-language generation**
   - Determine whether translating all target languages in one LLM call or separate calls produces better reliability, latency and output consistency.

8. **YouTube embed limitations**
   - Validate the intended player/subtitle layout against current YouTube embedded-player requirements.
   - Prefer a separate subtitle region unless a compliant overlay mechanism is identified.

9. **Caption transport**
   - Compare WebSocket, SSE and managed realtime systems for simplicity and reconnect behaviour.

10. **Failure handling**
    - Confirm that every caption component can fail independently without affecting the livestream.

---

# 25. Suggested Prototype

The first prototype should minimize integration work.

## Sender

```text
Mixer audio
   ↓
Whisper
   ↓
semantic chunks
   ↓
LLM translation
   ↓
timestamp + translations
   ↓
WebSocket server
```

## Receiver

```text
Simple webpage
   │
   ├── YouTube IFrame Player
   │
   └── WebSocket caption client
              │
              ↓
       caption scheduler
              │
              ↓
       subtitle region
```

The prototype should initially support:

- English transcription;
- one translated language;
- basic timestamp synchronization;
- manual calibration if required;
- fullscreen receiver UI.

After synchronization is demonstrated to work reliably, add:

- additional languages;
- automatic timeline alignment;
- translation context;
- terminology glossary;
- monitoring and recovery;
- improved subtitle styling.

---

# 26. Success Criteria

The system should be considered successful when:

- the existing YouTube livestream remains unchanged;
- captions are generated entirely outside the video path;
- translated captions correspond correctly to the spoken content;
- subtitles appear synchronized with the receiving YouTube playback;
- meaningful sentence/chunk context can be used for translation without captions arriving late;
- multiple subtitle languages can be offered from one source transcript;
- receiving volunteers can operate the system through a simple webpage;
- failure of the subtitle system does not interrupt the livestream;
- the end-to-end subtitle experience remains usable during buffering or minor YouTube latency variation.

The central hypothesis to validate is:

> **YouTube's delivery latency provides enough headroom to perform source-side transcription and high-quality contextual translation before the corresponding video reaches the receiving location, while a custom receiving frontend can use the YouTube player's actual playback position to present those captions at the correct time.**