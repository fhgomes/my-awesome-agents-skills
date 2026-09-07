# Mobile Performance Guide (Flutter)

**Best used when:** you own a Flutter app — a fresh `flutter create` or a legacy one — with no performance practice, and you want frame numbers instead of "it feels smooth on my phone".
**Read before:** shipping a scrolling list, an image feed, an animation, or accepting an AI-written screen that "should be performant".
**See also:** [performance-from-zero.md](./performance-from-zero.md) · [enforcement/README.md](./enforcement/README.md) · [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md)

A dropped frame is visible; a slow query is not. A backend p95 of 400 ms hides inside a spinner — a list that stutters while the user's thumb is on the screen is judged instantly, and it is judged as "cheap app". The standing review question is the same one the backend uses — **"Can this change hurt performance? Query inside a loop, load without pagination, objects piling up in memory."** On mobile it reads as: work inside `build()`, a list without a page, images decoded at full resolution. The companion rule keeps you honest in the other direction: **maintainable > fast, optimize only when measured**.

Your budget is fixed by the display, not by your opinion ([docs.flutter.dev/perf/best-practices](https://docs.flutter.dev/perf/best-practices)):

| Refresh rate | Total frame budget | Split |
|---|---|---|
| 60 Hz | **16 ms** | ~8 ms build (UI thread) + ~8 ms render (raster thread) |
| 120 Hz | **8 ms** | proportionally tighter — 120 Hz devices are the ones people notice jank on |

Two categories run through everything below. Hygiene is not optimization — it is the difference between a screen that survives 5 000 items and one that dies at 300; measuring it is redundant, skipping it is how "smooth on my phone with 20 rows" ships. Everything here is a recommendation; the gates that make it stick live in [enforcement/](./enforcement/README.md).

| Category | When you apply it | Mobile examples |
|---|---|---|
| **Structural hygiene** | Always, in review, no measurement needed | `ListView.builder` for any list that can grow; `const` constructors; no I/O in `build()`; paginated data source; images with a decode size; timeouts on every HTTP call |
| **Optimization** | Only after a measurement names the hotspot | `RepaintBoundary`; `itemExtent`; `AutomaticKeepAliveClientMixin`; caching a computed value; `compute()` for a payload you measured as slow |

---

## 1. Measure first: profile mode on a real device

Debug mode and emulators lie. Debug builds are JIT-compiled with assertions on and can be an order of magnitude slower; emulators do not have your users' GPU or thermal behaviour. **Every performance number comes from a physical device in profile mode** — and preferably the cheapest device you officially support.

```bash
flutter devices                      # list connected devices
flutter run --profile -d <device-id> # profile mode on a physical device
```

Turn on the performance overlay in one of three ways ([docs.flutter.dev/perf/ui-performance](https://docs.flutter.dev/perf/ui-performance)): press `P` in the `flutter run` console (fastest), use the overlay button in DevTools, or set `MaterialApp(showPerformanceOverlay: true)` for a build you hand to someone else — and remember to remove it.

Reading the two graphs: **top = raster thread** (GPU work: what you painted), **bottom = UI thread** (Dart: `build`, layout, your logic). Each bar is one frame; the horizontal line is the 16 ms budget; **a red bar is a frame that blew the budget**. Which graph is red tells you where to look — red on the bottom means your Dart code, red on the top means painting (clips, shadows, opacity, saveLayer).

DevTools does the rest ([docs.flutter.dev/tools/devtools/performance](https://docs.flutter.dev/tools/devtools/performance)):

| DevTools view | What you get | Use it for |
|---|---|---|
| Performance → frame chart, then timeline events | Per-frame UI and raster time; the build/layout/paint tree for the frame you select | Finding *which* frame is janky, then *what* inside it is slow |
| Performance → rebuild stats | Widget rebuild counts per frame | Widgets rebuilding that had no reason to |
| Performance → enhanced tracing ("Track Layouts", "Track Paints") | Marks intrinsic/layout/paint passes | Intrinsic passes and repaint storms |
| CPU profiler / Memory view | Sampled Dart stacks; heap, allocations, snapshots | A method eating the UI thread; leaks and image-cache growth |

**Rule: no frame number, no performance claim.** Reject "this is smoother now" without a before/after frame time from profile mode on a device.

---

## 2. `build()` discipline

`build()` runs on every frame that touches this widget. Treat it as a pure function of its inputs: no I/O, no `await`, no network, no file access, no heavy compute, no allocation you can hoist.

```dart
// GOOD — early return, cheap branches, const leaves
@override
Widget build(BuildContext context) {
  if (isLoading) return const CircularProgressIndicator();
  if (hasError) return const ErrorView();
  return ContentView(items: items);
}

// GOOD — const constructors wherever the subtree is constant
const Text('Hello');
const SizedBox(height: 16);
```

Rules, in the order they pay off:

| Rule | Why |
|---|---|
| **`const` constructors wherever possible** | A `const` widget is canonicalized: it is not rebuilt and it is not re-elemented. Free, permanent, applies to most leaf widgets |
| **Split big widgets into small ones, and localize `setState()`** | Flutter rebuilds subtrees, not files: a 400-line `build()` is one rebuild unit, five widgets are five. Call `setState` on the smallest `StatefulWidget` that owns the changing state, never on the page for a toggle in a row |
| **Prefer a `StatelessWidget` over a `_buildX()` helper method** | A helper returns a widget with no identity — Flutter cannot skip it. A widget class can be `const` and can be skipped |
| **Never override `operator ==` on a widget** | It defeats the framework's cheap identity check and makes rebuilds *more* expensive ([best practices](https://docs.flutter.dev/perf/best-practices)) |
| **Do the work in the store/service, not the widget** | Sort, filter and format when the data arrives, not on every frame |

Keep the observed scope small. In a MobX-based architecture (Pages → Stores → Services → Models, with GetIt for DI), wrap the *smallest* widget that reads an observable in `Observer`, not the whole page — one page-level `Observer` means one changed field repaints the screen. Same idea elsewhere: Riverpod `ref.watch(provider.select((s) => s.field))`; Bloc `BlocBuilder(buildWhen: (prev, curr) => prev.field != curr.field)`; plain `setState` on a smaller `StatefulWidget`, or `ValueListenableBuilder`.

---

## 3. Lists and grids

The single most common generated anti-pattern, and the one that always survives review because it works with 20 items:

```dart
// BAD — builds every item up front, holds every element in memory
ListView(
    children: items.map((item) => ItemTile(item: item)).toList(),
)

// GOOD — lazy: builds only what is on screen (plus a cache extent)
ListView.builder(
    itemCount: items.length,
    itemBuilder: (_, i) => ItemTile(items[i]),
)
```

The same rule for every scrollable: `GridView.builder`, `PageView.builder`, `SliverList`/`SliverChildBuilderDelegate` inside a `CustomScrollView`. `ListView(children: [...])` is acceptable only for a fixed, hand-written, small set of children (a settings screen), and only because the count is bounded by the source code.

| Technique | When |
|---|---|
| `itemExtent: 72`, or `prototypeItem: const ItemTile.placeholder()` | All rows have the same height — lets Flutter skip layout to compute scroll geometry. Big win on long lists; `prototypeItem` when you would rather not hard-code the number |
| `AutomaticKeepAliveClientMixin` | **Sparingly** — each kept-alive item stays in memory and keeps its state; use it for a video player in a feed, not for every row |
| `SliverList` inside a `CustomScrollView` | The list must share one scroll with headers |

**Pagination is part of the widget's contract, not just the backend's.** Use the same page/size contract as the API — `page`, `size`, **max size 100** — and load the next page from a scroll listener or an infinite-scroll controller. A screen that calls a "get all" endpoint is a screen that will one day download 40 000 rows over mobile data. Full-list operations (`items.where(...)` over everything, sorting the whole dataset on each build) belong in the query, not in the client.

---

## 4. Images

> A mobile app hotfix titled "resolve memory leak in image loading" exists in our history. The screen was a scrolling list of full-resolution images decoded at their original size for 120-pixel thumbnails.

A decoded image costs roughly `width × height × 4` bytes in RAM regardless of how small you draw it. A 4000 × 3000 photo is ~48 MB decoded. Twenty of them in a scrolling list is the whole heap.

```dart
// GOOD — cached, and decoded at the size you will actually draw
CachedNetworkImage(
  imageUrl: url,
  memCacheWidth: 240,          // 120 dp thumbnail at 2x
  placeholder: (_, __) => const ColoredBox(color: Color(0x11000000)),
  errorWidget: (_, __, ___) => const Icon(Icons.broken_image),
)

// GOOD — no extra package: cap the decode size
Image.network(url, cacheWidth: 240)
```

| Rule | Detail |
|---|---|
| Resize server-side, and always cap the decode | The cheapest fix is not sending a 4000 px JPEG to a phone — ask the API for a thumbnail variant. Then set `cacheWidth`/`cacheHeight` (or `memCacheWidth`/`memCacheHeight` with [`cached_network_image`](https://pub.dev/packages/cached_network_image)) to the *drawn* size in physical pixels |
| Cache on disk for repeat views | `cached_network_image` gives you disk + memory cache and a placeholder in one widget |
| `FadeInImage`, not `Opacity` | Fading with `Opacity` triggers `saveLayer` every frame; `FadeInImage` is built for this |
| `precacheImage(...)` for hero images | In `didChangeDependencies()`, for the one image the next screen opens with — never for a list. Watch the memory view: heap that climbs while scrolling and never returns is a decode-size problem |

---

## 5. Expensive things you do not see

These are cheap to write and expensive to render. They are usually what turns the **raster** graph red.

| Thing | Cost | Do instead |
|---|---|---|
| `Opacity` inside an animation | Forces `saveLayer` on every frame | `AnimatedOpacity`, `FadeInImage`, or animate a color's alpha |
| `saveLayer` (explicit or implied) | Allocates an offscreen buffer and composites it — one of the most expensive operations in the framework | Avoid the widget that implies it; measure with "Track Paints" |
| `Clip.antiAliasWithSaveLayer` | The most expensive clip mode | `Clip.hardEdge` or `Clip.antiAlias`; better, use a rounded `BoxDecoration` and no clip at all |
| Shadows / `BackdropFilter` in a scrolling list | Repainted per frame, per item | Flat cards, or one shadow on the container |
| Intrinsic passes (`IntrinsicHeight`, `IntrinsicWidth`, some `Table` uses) | Extra layout walk over the subtree — superlinear in a nested layout | Fixed sizes, `Flexible`/`Expanded`, or `itemExtent`. Confirm with DevTools "Track Layouts" |
| Very large `Stack`s that repaint together | One changing child repaints all of them | `RepaintBoundary` around the animating child — **after** the profiler shows the repaint |

`RepaintBoundary` is an **optimization**, not hygiene: it costs memory and a composited layer. Add it when the raster graph and "Track Paints" show a subtree repainting for no reason, then re-measure to confirm the gain. Scattering it "for performance" makes things worse.

Shader-compilation jank — the stutter the *first* time an animation runs — is handled by Flutter's default renderer, Impeller, which precompiles its shaders instead of compiling them at draw time ([docs.flutter.dev/perf/rendering-performance](https://docs.flutter.dev/perf/rendering-performance), [/perf/impeller](https://docs.flutter.dev/perf/impeller)). If you still see first-run jank, confirm which renderer your build actually uses before chasing SkSL warm-up flags — the flags and their availability change between releases. **[check for your Flutter version]**

---

## 6. Async and isolates

The UI isolate draws your frames. Anything that occupies it for more than a few milliseconds is a dropped frame, no matter how well written it is.

```dart
// BAD — 3 MB of JSON parsed on the UI isolate: guaranteed jank
final data = jsonDecode(response.body) as List;

// GOOD — parse off the UI isolate
final body = response.body;
final data = await Isolate.run(() => jsonDecode(body) as List);  // Dart 2.19+
final data = await compute(_parsePayload, body);                 // the classic form
```

| Rule | Detail |
|---|---|
| Big JSON off the UI isolate; no blocking work in `build()`, `initState()` or a scroll listener | Use `Isolate.run` / `compute` when a payload is large or a parse is measurably slow — also for cryptography, image processing, sorting tens of thousands of items. Small payloads are not worth the hand-off: measure, do not guess |
| Keep HTTP interceptors cheap | A Dio interceptor runs on every request; no crypto, disk reads or big logging there |
| Timeouts on every outbound call | `Dio(BaseOptions(connectTimeout: ..., receiveTimeout: ...))`. A hung request is a spinner forever |
| Debounce search inputs | 300–400 ms after the last keystroke. Typing "invoice" without debounce is 7 requests and 7 rebuilds |
| Cancel work the user left behind | Cancel tokens on navigation; check `mounted` before `setState` after an `await` |

---

## 7. App size

Users on cheap devices and metered data uninstall large apps. Measure it, do not estimate it ([docs.flutter.dev/perf/app-size](https://docs.flutter.dev/perf/app-size)):

```bash
flutter build apk --analyze-size --target-platform android-arm64
flutter build appbundle --analyze-size
flutter build ios --analyze-size
```

Each run prints a size breakdown and writes a `*-code-size-analysis_*.json` file. Open it in DevTools → **App Size** tool (tree view and treemap, down to individual files and Dart AOT functions) to see which package or asset is actually costing you.

| Flag / technique | Effect |
|---|---|
| `--split-debug-info=./symbols` | Moves debug symbols out of the binary — a large reduction. Keep `./symbols` to symbolicate crashes |
| `--obfuscate` (with `--split-debug-info`); `--split-per-abi` (APK only) | Obfuscation is a small extra reduction, mostly a security measure. `--split-per-abi` gives one APK per architecture instead of a fat one — irrelevant for an App Bundle, which splits automatically |
| Tree-shaken icons | On by default for release builds when icon data is const — check the "Font asset ... tree-shaken" line in the build output |
| Deferred components | Split rarely used features out of the initial download. Real work; do it when the analysis names a big feature |
| Audit assets | Compress PNG/JPEG, drop unused resolutions, remove fonts you stopped using |

**Budget:** track the release AAB size in CI on every merge to the main branch and **fail the PR on more than +500 KB without a written justification**. The number is arbitrary until you own it — the point is that nobody adds 12 MB by accident.

---

## 8. Startup

Time to first meaningful frame is the only performance number a user experiences before they can blame the network.

```bash
flutter run --trace-startup --profile -d <device-id>   # writes build/start_up_info.json
```

The JSON carries `timeToFirstFrameMicros`, `timeToFrameworkInitMicros` and `timeToFirstFrameRasterizedMicros`; the first one is your headline number. The flag is a `flutter` tool feature documented in the tool's own help and issue tracker rather than on docs.flutter.dev ([flutter/flutter#79338](https://github.com/flutter/flutter/pull/79338) is where the output path became configurable) — **[check for your Flutter version]** with `flutter run --help` before wiring it into a script, and profile mode only: debug numbers are an order of magnitude off.

| Rule | Detail |
|---|---|
| Nothing heavy in `main()` before `runApp`; defer analytics, crash reporting and remote config | Every millisecond before `runApp` is a millisecond of white screen. Initialize the rest after the first frame (`WidgetsBinding.instance.addPostFrameCallback`), except a service that must catch startup crashes |
| Lazy DI registrations | Prefer a lazy singleton (e.g. GetIt `registerLazySingleton`) for anything not needed on the first screen |
| No blocking I/O on the splash, and always measure a **cold** start on a low-end device | Reading a big local cache synchronously is the classic 2-second splash; warm starts on a flagship hide everything |

---

## 9. Automated frame tests

Manual profiling does not survive a busy sprint. Put one scroll benchmark in CI ([docs.flutter.dev/cookbook/testing/integration/profiling](https://docs.flutter.dev/cookbook/testing/integration/profiling)).

```dart
// integration_test/scrolling_test.dart
final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

testWidgets('scrolling the feed stays inside the frame budget', (tester) async {
  await tester.pumpWidget(const MyApp());
  await binding.traceAction(() async {
    await tester.scrollUntilVisible(itemFinder, 500.0, scrollable: listFinder);
  }, reportKey: 'scrolling_timeline');
});
```

```bash
flutter drive \
  --driver=test_driver/perf_driver.dart \
  --target=integration_test/scrolling_test.dart \
  --profile
```

- `traceAction` records the timeline for the action; `watchPerformance` watches `FrameTiming` for a block and reports it under a key.
- By default the report data is written to **`build/integration_response_data.json`** under the key `timeline`; a `perf_driver.dart` with a `responseDataCallback` that calls `TimelineSummary.summarize(...).writeTimelineToFile(...)` also produces `build/<key>.timeline_summary.json`.
- Assert on **average frame build time** *and* **worst frame build time** — an average of 9 ms with a 90 ms worst frame is a visible stutter. Fail the job on a regression against a recorded baseline.
- Run it on a **physical device or a device farm**, never an emulator. Emulator frame times are noise. Keep the benchmark to one or two flows; a flaky perf suite gets disabled within a month.

---

## 10. Review checklist (mobile)

- [ ] Every growable list uses `ListView.builder` / `GridView.builder` / `SliverList` — no `children: items.map(...).toList()`.
- [ ] The list is fed by a paginated endpoint (`page`, `size`, max 100), not by a "get all".
- [ ] `build()` has no I/O, no `await`, no network call and no heavy compute; expensive work happens in the store/service.
- [ ] `const` used everywhere it can be; new leaf widgets are `const`-constructible.
- [ ] The rebuild scope is the smallest one that reads the changed state (`Observer` / `select` / `buildWhen` on the subtree, not the page).
- [ ] Every network image has a decode cap (`cacheWidth`/`memCacheWidth`) and a cache; no full-resolution images in thumbnails.
- [ ] No `Opacity` inside animations; no `Clip.antiAliasWithSaveLayer`; no per-item shadows in a long list.
- [ ] `RepaintBoundary`, `itemExtent` and `AutomaticKeepAliveClientMixin` appear only with a measurement that justified them.
- [ ] Big payload parsing runs in `compute()` / `Isolate.run`; every HTTP call has explicit timeouts; search inputs are debounced.
- [ ] The claim "this is faster" comes with a profile-mode frame time or an `--analyze-size` diff from a physical device.

---

## 11. Same idea in React Native

| Concern | Flutter | React Native |
|---|---|---|
| Long lists, uniform row height | `ListView.builder` (never `ListView(children: map)`); `itemExtent` / `prototypeItem` | `FlatList` or [`@shopify/flash-list`](https://shopify.github.io/flash-list/), never `ScrollView` + `.map()`; `getItemLayout` on `FlatList` |
| Rebuild scope | `const`, small widgets, narrow `Observer`/`select` | `React.memo`, stable `keyExtractor`, `useCallback` on `renderItem` — **only where a profile shows the re-render** |
| Images | `cached_network_image`, `cacheWidth` | `react-native-fast-image` or `expo-image`; explicit `resizeMode` and sized sources |
| Profiler | DevTools Performance view + performance overlay | React DevTools Profiler, the Hermes sampling profiler, the in-app Perf Monitor |
| Off-thread work | `compute()` / `Isolate.run` | `InteractionManager.runAfterInteractions`, or a worklet / native module for real CPU work |
| Bundle size | `flutter build --analyze-size` + DevTools App Size | `react-native-bundle-visualizer` or a source-map explorer over the release bundle **[check]** |

The judgement is identical in both: lazy lists and bounded work are hygiene; memoization is an optimization that needs a profile behind it.

---

## 12. Day 1 / Week 1

### Greenfield (a new Flutter app)

| When | Do | Command / artifact |
|---|---|---|
| Day 1 | Create the project, the folder shape, and codegen so nobody hand-writes models | `flutter create --org com.yourcompany your_app` ; `mkdir -p lib/{core,features,shared}` ; `dart run build_runner build --delete-conflicting-outputs` |
| Day 1 | Run in profile mode on a physical device and read the overlay | `flutter run --profile`, then press `P` |
| Day 1 | Commit the budget (`perf-budgets.md`): 16 ms frame / 8 ms at 120 Hz, app-size ceiling, startup target | 3 lines, committed |
| Day 1 | Put the four hygiene rules in your AI instruction file (`AGENTS.md` / `CLAUDE.md`): builder lists, `const`, no I/O in `build()`, decode-capped images | see [enforcement/README.md](./enforcement/README.md) |
| Week 1 | First size baseline recorded in the PR; flavors (`dev`/`prod`) so profile builds are routine | `flutter build appbundle --analyze-size` |
| Week 1 | One `integration_test` scroll benchmark on the main list, run on a device | `flutter drive --driver=... --target=... --profile` |

### Legacy (an existing Flutter app with no practice)

| When | Do | Command / artifact |
|---|---|---|
| Day 1 | Pick the one screen users call "laggy". Run it in profile mode on a real device and **write the frame times down** | `flutter run --profile` + overlay + DevTools frame chart |
| Day 1 | Grep the anti-patterns, count them, and record the current release size before changing anything | `grep -rn "ListView(" lib \| grep -n "children"` ; `grep -rn "Image.network" lib` ; `flutter build appbundle --analyze-size` |
| Week 1 | Fix the top three by user impact — usually builder list, image decode cap, rebuild scope — and re-measure each | before/after frame time in the PR |
| Week 1 | Add pagination to the one list that loads everything | same `page`/`size` contract as the API |
| Week 1 | Add the scroll benchmark for the screen you fixed, and section 10 to the PR template | `integration_test` + `traceAction`; see [enforcement/README.md](./enforcement/README.md) |

---

## 13. Asking an AI for performant Flutter code

Generated Flutter code fails predictably: `ListView(children: ...)` because it is shorter, images with no decode cap, a page-wide rebuild scope, `RepaintBoundary` sprinkled when you say "make it performant", and a summary claiming smoothness nobody measured. Constrain it up front:

```text
Context: Flutter <version>, <state library>, list of up to <N> items from a paginated API.
Task: <the screen>.
Constraints:
- Any growable list uses ListView.builder / GridView.builder / SliverList. Never children: items.map(...).toList().
- The data source is paginated (page + size, max size 100).
- No I/O, await or heavy compute inside build(). const constructors wherever possible.
- Network images have an explicit decode size (cacheWidth/memCacheWidth) and a cache.
- Rebuild scope is the smallest widget that reads the changed state.
- Do NOT add RepaintBoundary, keep-alives or isolates unless I ask.
Verification: tell me which widgets rebuild when one item changes, and how you would measure the
frame time. Do not claim smoothness you did not measure in profile mode on a device.
```

Then check the output yourself: run it in profile mode, read the two graphs, and reject any "optimized" diff that arrives without a number.

## Sources & further reading

- Flutter, "Performance best practices" — frame budget (16 ms at 60 Hz: 8 build + 8 render, 8 ms at 120 Hz), `build()` discipline, `const`, builder lists, `Opacity`/`saveLayer`/clip costs, intrinsic passes, never override `operator ==`: https://docs.flutter.dev/perf/best-practices
- Flutter, "Performance profiling" — profile mode, the performance overlay, reading the raster and UI graphs: https://docs.flutter.dev/perf/ui-performance
- Flutter DevTools, "Use the Performance view" — frame chart, timeline events, rebuild stats, enhanced tracing: https://docs.flutter.dev/tools/devtools/performance
- Flutter, "Rendering performance" and "Impeller" — first-run animation jank and the default renderer: https://docs.flutter.dev/perf/rendering-performance · https://docs.flutter.dev/perf/impeller
- Flutter, "Measuring your app's size" — `--analyze-size`, the code-size-analysis JSON, DevTools App Size tool, `--split-debug-info`, obfuscation: https://docs.flutter.dev/perf/app-size
- Flutter cookbook, "Measure performance with an integration test" — `traceAction`, `reportKey`, `perf_driver.dart`, `flutter drive --profile`: https://docs.flutter.dev/cookbook/testing/integration/profiling ; `watchPerformance` and the default `build/integration_response_data.json` report: https://api.flutter.dev/flutter/package-integration_test_integration_test/IntegrationTestWidgetsFlutterBinding/watchPerformance.html
- `cached_network_image` — disk + memory image cache, `memCacheWidth`/`memCacheHeight`: https://pub.dev/packages/cached_network_image
- FlashList (Shopify) — the React Native list replacement referenced in section 11: https://shopify.github.io/flash-list/

## Related

- [performance-from-zero.md](./performance-from-zero.md) — the language-agnostic entry point: golden signals, budgets, the eight ways an AI writes slow code
- [backend-performance-guide.md](./backend-performance-guide.md) — the API behind these screens: pagination contract, N+1, indexes, caching ladder
- [frontend-performance-guide.md](./frontend-performance-guide.md) — the same discipline on the web: Core Web Vitals, bundles, render discipline
- [enforcement/README.md](./enforcement/README.md) — instructions, hooks and CI gates that make these rules stick
- [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md) — the agent skill that reviews for all of this

_Last reviewed: 2026-09-07._
