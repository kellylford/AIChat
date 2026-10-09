# How The Chat Place chooses what speaks (Windows)

Written for issue #98 ("TCP not speaking through NVDA"), before any code changes. It describes
what the code does today, why NVDA users hear a Windows voice, and the options for fixing it.

## The pieces

| Piece | File | Job |
|---|---|---|
| Settings | `thechatplace/speech.py` (`SpeechSettings`) | Stores `engine`, `voice`, `rate_preset` in `%APPDATA%\TheChatPlace\speech.json`. Default engine is `auto`. |
| Probe | `thechatplace/speech/speak-voices.ps1`, called by `list_speech_options()` | Runs once on a background thread at startup. Reports screen readers and system voices as JSON. Its result fills the **Speech** choice in Settings. |
| Speaker | `speech.py` (`Speaker.speak`) | For each announcement, writes the text and a small JSON config to `%TEMP%\thechatplace-speak\`, then starts a hidden `powershell.exe` running `speak-engine.ps1`. One utterance at a time; an interrupting one kills the previous process. |
| Engine | `thechatplace/speech/speak-engine.ps1` | Picks a route and speaks. Bundled verbatim from ClaudeSpeak (via IDT). |

## How the engine picks a route

`speak-engine.ps1` has four routes and tries them in an order set by the configured engine. The
first route that reports success wins; the rest are skipped.

| Configured engine | Order tried |
|---|---|
| `auto` (Automatic) | JAWS, NVDA, OneCore, SAPI |
| `jaws` | JAWS, NVDA, OneCore, SAPI |
| `nvda` | NVDA, JAWS, OneCore, SAPI |
| `onecore` (a Windows voice) | OneCore, SAPI |
| `sapi` (a Windows voice) | SAPI, OneCore |

What each route needs in order to succeed:

- **JAWS**: a process named `jfw` is running, and the `FreedomSci.JawsApi` COM object can be
  created. JAWS registers that COM object when it is installed, so this works on any normal JAWS
  install. Calls `SayString(text, interrupt)`.
- **NVDA**: a process named `nvda` is running, **and** a file named `nvdaControllerClient*.dll`
  of the right CPU architecture is found in one of:
  `%USERPROFILE%\.claude`, `%ProgramFiles%\NVDA`, `%ProgramFiles(x86)%\NVDA`,
  `%LOCALAPPDATA%\Programs\NVDA` (searched four folders deep). The DLL is copied to
  `%TEMP%\claude-speak-nvda\nvdaControllerClient.dll`, compiled against with `Add-Type`, then
  `nvdaController_testIfRunning()` must return 0 before `speakText` is called. The app passes
  `nvdaClientDll: ""`, so it never supplies a DLL of its own.
- **OneCore**: the WinRT speech synthesizer. With no voice chosen, it uses the Windows default
  voice (on this PC, David). Rate defaults to 3.0, the middle of its scale.
- **SAPI**: the older desktop voices, used only if OneCore fails.

Every run writes `%TEMP%\claude-speak\last-route.log` saying which route spoke and which failed.
That file is shared with ClaudeSpeak's Claude Code hook and holds only the latest utterance.
The app's own `%TEMP%\thechatplace-speak\speech.log` records what was handed to the engine, but
not which route spoke.

## What the Settings choices actually change

The Python side treats JAWS, NVDA and Automatic alike: no voice and no rate are sent for any of
them (`resolved_rate()` is `None`, because `RATE_PRESETS` has no `jaws`/`nvda`/`auto` key), and the
dialog shows "Voice and rate follow your screen reader's own settings."

The only difference is the order in the table above:

- **Choosing JAWS does nothing that Automatic doesn't.** The order is identical. The one visible
  difference is in `last-route.log`: if something other than JAWS speaks, it adds a "fell back"
  warning line, which Automatic never adds.
- **Choosing NVDA** tries NVDA before JAWS. That only matters when both are running. It does not
  make NVDA work when it otherwise wouldn't.

### Why the picker shows JAWS but not NVDA

The probe lists a screen reader only when it is "available", and it means something different
for each:

- JAWS is available when the COM object can be created, i.e. JAWS is installed. Running or not,
  it appears (with "(not running right now)" if it isn't).
- NVDA is available only when the probe finds a controller client DLL of the right
  architecture. NVDA being installed and running is not enough. With no DLL, NVDA is left out of
  the picker entirely, and nothing tells the user why.

Two inconsistencies make this harder to see:

1. If the probe hasn't finished, timed out (25 seconds), or failed, Settings shows
   `default_options()`, which **always** lists both JAWS and NVDA. So the NVDA entry can appear on
   one start and be missing on the next, depending only on probe timing.
2. The probe searches `%USERPROFILE%\Downloads` for the DLL; the engine does not. A DLL sitting in
   Downloads makes the picker offer NVDA while the engine still can't use it.

## Why NVDA users hear a Windows voice (issue #98)

**The NVDA controller client DLL does not ship with NVDA**, and The Chat Place doesn't ship it
either. NV Access distributes it as a separate download for developers. A normal NVDA user has
never installed it.

So on a normal NVDA machine, with Automatic selected:

1. JAWS route: `jfw` isn't running, fails.
2. NVDA route: `nvda` is running, but no DLL is found, fails.
3. OneCore route: speaks with the Windows default voice. **This is what the user hears.**

Reproduced on this PC: NVDA 2026.1.1 is installed in `C:\Program Files\NVDA` (64-bit). There is no
`nvdaControllerClient*.dll` anywhere under it, under `%USERPROFILE%\.claude`, or in the staging
folder. Automatic therefore always lands on OneCore, whose default voice here is David, while
NVDA itself is set to Zira. That matches Kelly's report exactly. ClaudeSpeak works on Kelly's
setups only because its `voice-setup` skill told the user to put the DLL in `%USERPROFILE%\.claude`
by hand; The Chat Place's users have no such step.

### The "intermittent" part of the report

The reporter says some starts speak through NVDA and some don't. The code as written cannot
reach NVDA at all without the DLL, so either they have a DLL somewhere the engine sometimes finds,
or what sounds like "the app speaking through NVDA" is NVDA reading something on its own
(a focus change, the status bar, a dialog). Candidate explanations to check:

- **NVDA reading the UI, not our announcement.** Most likely, if they have no DLL. Some app
  messages also show in places NVDA reads by itself, so a few announcements reach NVDA's voice
  and the rest come through David.
- **Startup race.** If the app starts before NVDA (at sign-in, for example), every route check
  happens per utterance, so this alone shouldn't stick. But it can make the picker differ between
  starts (see above).
- **A DLL in an odd place.** If one is in Downloads, the picker offers NVDA but the engine never
  uses it.
- **`testIfRunning` failing now and then**, for instance when NVDA is restarting or between
  profiles.

To tell these apart, ask the reporter for `%TEMP%\claude-speak\last-route.log` straight after an
announcement in the wrong voice, and whether `nvdaControllerClient*.dll` exists anywhere on their
machine. (Once fixed, the app should record the route itself; see below.)

## Other weaknesses found along the way

- **Slow NVDA path.** Each utterance starts PowerShell, searches four folders recursively, and
  compiles C# with `Add-Type`. That's around a second or more before NVDA starts talking, every
  time.
- **No way to see the route from the app.** Neither the user nor a bug report can tell which route
  spoke without digging in `%TEMP%`. The shared `last-route.log` can be overwritten by ClaudeSpeak.
- **Architecture.** The DLL must match the process that loads it (`powershell.exe`, x64 or
  ARM64), not NVDA. Any DLL we ship needs both x64 and ARM64 builds.
- **Silent fallback.** The design deliberately falls back so something is always said, but for a
  screen-reader user the fallback is worse than useless: a second voice talking over NVDA, in a
  voice they didn't choose.

## What other projects for blind users do

Researched October 2026 from source on GitHub. Two findings hold across every project checked:

- **Nobody relies on NVDA to supply the controller client.** They either ship the DLL next to the
  app or, in the newest library, build NVDA's RPC interface in so no DLL is needed.
- **Nobody starts a subprocess for each utterance.** They all call the screen reader from the
  app's own process (ctypes, FFI or COM), loaded once.

| Project | How it reaches NVDA / JAWS | Ships the NVDA DLL? | Falls back to a system voice when… |
|---|---|---|---|
| [accessible_output2](https://github.com/accessibleapps/accessible_output2) (Python; used by TWBlue, a wx app) | ctypes `nvdaControllerClient`, NVDA counts as active if `testIfRunning()==0`; JAWS through COM plus the `JFWUI2` window | Yes, old 32/64-bit builds, no ARM64 | …the screen reader check fails, silently. Same symptom as ours if the DLL won't load. |
| [Tolk](https://github.com/ndarilek/tolk) / [cytolk](https://github.com/pauliyobo/cytolk) | NVDA: window `wxWindowClassNR`/"NVDA" **and** `testIfRunning()`, because System Access pretends to be NVDA. JAWS: `JFWUI2` window, then COM | Yes, x86/x64 | …only if the app turns SAPI on (`Tolk_TrySAPI`); off by default |
| [UniversalSpeech](https://github.com/qtnc/UniversalSpeech) (used by the NVGT game engine) | Loads `nvdaControllerClient.dll` from the app folder | The app supplies it (NVGT [bundles it](https://github.com/samtupy/nvgt/blob/main/src/bundling.cpp)) | …all screen readers fail; SAPI last |
| [Prism](https://github.com/ethindp/prism) (C++; Python package `prismatoid` with x64 and ARM64 wheels, .NET, Rust) | Talks to NVDA's RPC endpoint directly from NVDA's IDL; JAWS through COM; also UIA, OneCore, SAPI | **No DLL needed** | …a screen reader backend fails to start. Its NVDA connection isn't retried after NVDA restarts. Successor to SRAL, now archived. |
| NV Access's own [examples](https://github.com/nvaccess/nvda/tree/master/extras/controllerClient) | `DllImport` / ctypes on the DLL | Yes, that's the intended use | — |

**The controller client itself** ([readme](https://github.com/nvaccess/nvda/blob/master/extras/controllerClient/readme.md),
[license](https://github.com/nvaccess/nvda/blob/master/extras/controllerClient/license.txt)):

- LGPL 2.1. Shipping the unmodified DLL with the app is allowed.
- Downloaded from `https://download.nvaccess.org/releases/stable/nvda_<version>_controllerClient.zip`
  (currently 2026.2). It has `x86/`, `x64/`, `arm64/` and `arm64ec/` folders, each with a
  `nvdaControllerClient.dll`.
- It must match the **calling process**, not NVDA. NVDA reaches it over local RPC, so 64-bit
  NVDA 2026 changes nothing. Our x64 frozen app needs the x64 DLL, including under emulation on
  ARM64 Windows.
- API 2.0 (NVDA 2024.1) added `speakSsml`. API 3.0 (NVDA 2026.3) adds `isSpeaking`. On an older
  NVDA, calls to newer functions return error 1717. `speakText` and `cancelSpeech` work on all
  versions.
- NV Access asks apps not to speak private text while Windows is locked or a secure screen is up,
  because NVDA runs there too.

**Ways that don't need an interface for each screen reader, and why they don't fit as the main path:**

- **UIA notification events** (`UiaRaiseNotificationEvent`): NVDA [drops them from background
  apps](https://github.com/nvaccess/nvda/blob/master/source/NVDAObjects/UIA/__init__.py), and our
  announcements mostly happen while the user is elsewhere. wx also has no UIA provider, so we'd
  have to write one with comtypes. They would help only Narrator, and JAWS while our window is in
  front.
- **Live regions:** NVDA filters these from background apps too.
- **Windows toast notifications:** NVDA, JAWS and Narrator all read toasts from any app. The Chat
  Place already sends them (#20), so they are the natural backup when the screen reader can't be
  reached. Do Not Disturb hides them, though, and they're shorter than a full reply.
- **A companion NVDA add-on:** users would have to install it, and NVDA's yearly add-on API bumps
  would keep breaking it. No mainstream app does this for plain speech.

**On falling back to a system voice:** Tolk makes SAPI opt-in for a reason. A second voice
talking over a running screen reader is generally treated as a defect, and accessible_output2's
silent fallback is the exact behaviour reported in #98.

## Options for the fix

**A. Ship the NVDA controller client with the app (required).** This is what every library and app
above does. Take `x64/` and `arm64/` `nvdaControllerClient.dll` from NV Access's controller client
zip, put them under `thechatplace/speech/nvda/<arch>/` with NV Access's `license.txt`, and add them
to the three PyInstaller command lines and the smoke test. NVDA then works on every machine
where NVDA is running, with no setup by the user.

**B. Call the screen readers from the app's own process.** Load the bundled DLL once with
`ctypes` and call `speakText` / `cancelSpeech`. Reach JAWS through COM. That needs a new dependency (`comtypes` or `pywin32`; the
app has neither today), or a small hand-written `ctypes` IDispatch call. Every project above does it this way. It removes the PowerShell
start, the folder search and the `Add-Type` compile on each NVDA utterance, and it lets the app
know which route spoke. Keep `speak-engine.ps1` only for OneCore/SAPI, which need a process to
kill in order to stop mid-sentence. Detect NVDA as Tolk does: the NVDA window **and**
`testIfRunning() == 0`. Detect JAWS by its `JFWUI2` window before COM, because the COM object can
be created when JAWS isn't running. Retry the connection on each utterance so an NVDA restart
doesn't break it. Skip private text when Windows is locked, as NV Access asks.

*Alternative to A + B:* use Prism (`prismatoid`), which reaches NVDA with no DLL and has x64 and
ARM64 wheels. It's newer and less proven, and it's MPL-2.0 C++ we'd have to bundle and track.
Not recommended as the first step. Our needs are two functions on one DLL.

**C. Don't fall back to a system voice while a screen reader is running.** If NVDA or JAWS is
running but the call fails, don't talk over it in another voice. Use the Windows notification
(toast) the app already sends (#20), which screen readers read from background apps, and put the
reason in the status bar and Settings once. OneCore/SAPI stay for when no screen reader is
running, or when the user picks a Windows voice on purpose.

**D. Make the picker honest.** List NVDA whenever it is installed, with a reason when it can't be
reached. Make `default_options()` match what the probe would report. Once A is in, NVDA is always
"available" when installed.

**E. Record the route in the app.** With B, the app knows which route spoke. Log it in
`speech.log` (not the `last-route.log` shared with ClaudeSpeak) and include it in **Help, Report
a Bug**, so the next report like #98 carries the answer.

**Not worth doing:** UIA notifications or live regions as the main path (NVDA ignores them from
background apps), and a companion NVDA add-on (installation burden and yearly breakage).

Suggested scope for #98: **A + B + C + D + E**. B is the biggest piece, but it's what makes the
others simple. Without it we keep patching a PowerShell script shared with ClaudeSpeak. The
README's speech section and the release notes would say NVDA works out of the box, and the
licence line would go in the README's credits.

## Decisions and what was built (9 October 2026)

Kelly chose A, B, C and D, and E came with B:

1. **Ship the DLL.** `thechatplace/nvda/x64` and `arm64` hold NV Access's 2026.2
   `nvdaControllerClient.dll`, unmodified, with `license.txt` and a README giving the source and
   SHA-256. They're added to the Windows build only, not the Mac one.
2. **Call screen readers from the app.** `thechatplace/screen_readers.py` loads the DLL once with
   ctypes and reaches JAWS through `comtypes` (new, Windows only). Each is tried only if its
   process (`jfw.exe`, `nvda.exe`) is running; NVDA must also pass `testIfRunning`. The speaker's
   worker thread does it, with COM set up on that thread. `speak-engine.ps1` is unchanged and now
   runs only for Windows voices: a screen-reader setting with no screen reader running hands it
   `onecore`, so it can't go looking for one itself.
3. **No Windows voice over a running screen reader.** If one is running but none takes the text,
   nothing is spoken. The reason goes beside the announcement in the status bar, to one Windows
   notification (screen readers read those), and to a read-only "Speech problem" box in Settings
   that Tab reaches. Each new reason is reported once, until speech works again. While Windows is
   locked or on a secure screen (`platform_paths.windows_locked`), nothing is sent.

   After the code review: only processes in the user's own Windows session count (JAWS also runs
   at the sign-in screen, in session 0 or the console session, and counting it silenced
   everything). NVDA also counts as running when it answers `testIfRunning`, whatever its process
   is called. Each JAWS or NVDA call runs on a helper thread with a 3-second deadline, so a hung
   screen reader can't stop all speech; while a hung call is still out, nothing more is sent.
   Error text is reduced to codes (`error_code`), so no message can carry a path into a report.
4. **Picker:** JAWS and NVDA stay. NVDA is listed whenever the probe finds it installed or running.
   Automatic now reads "your screen reader, or a system voice when none is running".
5. **Route recorded:** `speech.log` gets a `route:` line after each screen-reader announcement, and
   Help, Report a Bug includes it as "Last announcement".

Tested in the vmtest VM (ARM64 Windows 11, NVDA 2026.2): from source on native ARM64 Python, which
uses the arm64 DLL, NVDA spoke and no Windows voice started. With the DLL removed, nothing was
spoken and the reason was reported. With NVDA stopped, the OneCore voice spoke. The x64
PyInstaller build, running under emulation, logged "route: spoke through NVDA" for its
announcements. On Kelly's PC, JAWS spoke through the in-process path.

Found along the way: the build doesn't include `msvcp140.dll`, so on a clean Windows without the
Visual C++ runtime, wx fails to load and the app exits at once. That predates this work and needs
its own issue.
