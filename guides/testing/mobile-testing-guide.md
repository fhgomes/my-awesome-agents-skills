# Mobile Testing Guide

**Best used when:** you own a Flutter app with no tests, or with a `test/` folder nobody runs because "it only works on my emulator".
**Read before:** adding `mockito` to `pubspec.yaml`, writing the first `testWidgets`, or asking an AI agent to "add tests to the app".
**See also:** [testing-from-zero.md](./testing-from-zero.md) · [e2e-testing-guide.md](./e2e-testing-guide.md) · [enforcement/README.md](./enforcement/README.md)

Primary stack here is Flutter with MobX stores, GetIt injection, Dio services and `build_runner` codegen — the shape `Pages -> Stores -> Services -> Models`. The last section maps the same ideas onto React Native.

---

## 1. Position: pyramid, with widget tests as the fat middle

Mobile is the one stack where the classic pyramid still holds, for a boring reason: the higher you go, the more a real device is involved, and a real device is slow and flaky. An emulator boot costs 30-90 seconds before a single assertion runs, and an iOS lane needs a macOS runner you pay for by the minute.

The cross-stack rule in this repo is **test at the highest layer that is still fast, deterministic and local**. For a Spring service that layer is the integration test with a real database. For Flutter it is the **widget test**: it runs in the Dart VM in milliseconds, renders the real widget tree, drives real taps, and never needs a device.

| Layer | Runs on | Speed each | Sees | Cannot see |
|---|---|---|---|---|
| Unit | Dart VM | ~1 ms | Store actions, service mapping, validators, pure math | Anything about rendering |
| Widget | Dart VM (`flutter_test`) | ~10-100 ms | Real widget tree, taps, input, rebuilds, disabled states | Platform channels, real network, native permissions |
| Golden | Dart VM | ~50 ms | Pixel output of a component | Behaviour |
| Integration | Emulator / simulator / device | 30 s - minutes | Real app assembly, plugins, navigation, native dialogs | Nothing cheaply — this is the expensive lane |

Volume follows cost: many unit, many widget, a handful of integration, a handful of goldens. If the suite is inverted — five widget tests, forty integration tests — the gate takes twenty minutes, someone marks it `continue-on-error`, and you are back to zero.

## 2. Toolchain

```yaml
# pubspec.yaml
dev_dependencies:
  flutter_test: { sdk: flutter }
  integration_test: { sdk: flutter }
  mockito: ^5.4.4
  build_runner: ^2.4.9
```

Verified against https://docs.flutter.dev/testing/integration-tests on 2026-09-07 — `integration_test` ships with the SDK (`sdk: flutter`), not from pub.

| Command | For |
|---|---|
| `flutter test` | The whole fast suite (unit + widget). This is your `npm test`. |
| `flutter test test/stores/user_store_test.dart` | **Single-test command.** Put it in the README. Every repo needs one. |
| `flutter test --name "should reject an expired code"` | One scenario by name |
| `flutter test --reporter expanded` | Per-test lines instead of a spinner — use in CI so a hang tells you where |
| `flutter test --coverage`, then `genhtml coverage/lcov.info -o coverage/html` | Coverage plus a readable report (needs `lcov`) |
| `flutter analyze` / `dart format --set-exit-if-changed lib test` | Static analysis and formatting. Part of the gate, not tests. |
| `dart run build_runner build --delete-conflicting-outputs` | Regenerates mocks, MobX `.g.dart`, serializers |

**mockito vs mocktail.** Use `mockito` when the project already runs `build_runner` — MobX and `json_serializable` projects do, so codegen costs nothing extra and you get null-safe generated mocks (`@GenerateMocks([AuthService])`, then import `<file>.mocks.dart`). Use `mocktail` when there is no codegen: no annotations, no generator step, `registerFallbackValue` instead of generated fakes. Pick one per repo, say which in `docs/testing.md`, do not run both.

**Lint is not a test.** `flutter analyze` catches a missing `const` constructor and a `ListView` built from `.map().toList()` instead of `ListView.builder`. Those are real performance defects on long lists, and they are analyzer and review concerns. No widget test will ever fail because a list scrolls badly.

## 3. Naming and structure

Mirror `lib/` into `test/`, one test file per source file: `lib/stores/user_store.dart` -> `test/stores/user_store_test.dart`, `lib/shared/components/primary_button.dart` -> `test/shared/components/primary_button_test.dart`.

- One `group` per class under test; test names read as `'should <behaviour> when <condition>'`; AAA in every test (Arrange, Act, Assert), with those comments when it runs past five lines.
- `setUp` builds fresh dependencies per test; `tearDown` disposes reactions, closes streams, resets GetIt (`await GetIt.I.reset()`).
- One behaviour per test. Three unrelated `expect`s means three tests — when it fails you want the name to tell you what broke.
- Never import a production constant to assert against it. Assert on the literal: `expect(result, MyService.maxRetries)` passes when both are wrong.

```dart
test('should calculate total when cart has items', () {
  final cart = Cart()..addItem(const Product(id: '1', price: 10.0));  // Arrange
  final total = cart.calculateTotal();                                // Act
  expect(total, equals(10.0));                                        // Assert
});
```

## 4. Unit tests: stores and services

A MobX store is where the app's decisions live, so it is where tests pay. Inject the service, mock the service, assert on observable state — never on which methods were called.

```dart
// test/stores/user_store_test.dart
@GenerateMocks([AuthService])
void main() {
  group('UserStore', () {
    late MockAuthService authService;
    late UserStore store;

    setUp(() {
      authService = MockAuthService();
      store = UserStore(authService: authService);
    });

    test('should authenticate and clear loading when login succeeds', () async {
      const user = User(id: '1', name: 'Test User');
      when(authService.login(any)).thenAnswer((_) async => user);
      await store.login('+15555550100');

      expect(store.isAuthenticated, isTrue);
      expect(store.currentUser, equals(user));
      expect(store.isLoading, isFalse);
    });

    test('should surface an error and clear loading when login fails', () async {
      when(authService.login(any)).thenThrow(AuthException('invalid_code'));
      await store.login('+15555550100');

      expect(store.isAuthenticated, isFalse);
      expect(store.errorMessage, isNotNull);
      expect(store.isLoading, isFalse);       // the spinner that never stops
    });
  });
}
```

Two details people skip and then regret:

1. **The failure test asserts `isLoading` is false.** A spinner that never stops is the most common mobile bug there is, and a happy-path test cannot see it. Assert the flag in both directions.
2. **No `verify()` as the primary assertion.** `verify(authService.login(any)).called(1)` says a method was called; it says nothing about whether the user is logged in. Use `verify` only when the call *is* the behaviour — an analytics event, an outbox write, a token revocation — and put the state assertion next to it anyway.

For async work, assert on the exception **type**, never its message. Messages are user-facing copy and get translated; types are contract.

```dart
await expectLater(service.getUser('123'), throwsA(isA<TimeoutException>()));
```

## 5. Widget tests

Pump the widget inside `MaterialApp` + `Scaffold`. Without them, anything touching `Theme`, `Directionality`, `MediaQuery` or `ScaffoldMessenger` throws and you will blame the test.

```dart
testWidgets('should show a spinner and hide the label when loading', (tester) async {
  await tester.pumpWidget(const MaterialApp(
    home: Scaffold(body: PrimaryButton(text: 'Submit', isLoading: true)),
  ));

  expect(find.byType(CircularProgressIndicator), findsOneWidget);
  expect(find.text('Submit'), findsNothing);
});
```

Disabled state is the same shape, asserted on the widget instead of on rendered output: pump with `onPressed: null`, then `expect(tester.widget<ElevatedButton>(find.byType(ElevatedButton)).onPressed, isNull)`.

**Finder priority.** Same rule as the web: find things the way a user perceives them.

| Priority | Finder | When |
|---|---|---|
| 1 | `find.text('Submit')` | Visible copy the user reads |
| 2 | `find.bySemanticsLabel('Close')` | Accessible name — also proves a screen reader can find it |
| 3 | `find.byType(PrimaryButton)`, `find.byIcon(Icons.close)` | Structural, when there is exactly one |
| 4 | `find.byKey(const Key('phone_field'))` | Last resort, the `testId` of Flutter — unlabelled fields, identical list rows |

If you reach for a `Key` because there is no label and no accessible name, that is usually the accessibility bug talking. Fix the widget; the finder gets easier.

**`pump` vs `pumpAndSettle`.** `pump()` advances one frame — use it after a synchronous `setState` or to catch an intermediate loading state. `pumpAndSettle()` repeats frames until none are scheduled — use it after navigation or a finite animation. It **hangs on an indefinite animation** (a looping spinner, a repeating `AnimationController`) and fails on timeout. When that happens do not raise the timeout; pump fixed frames instead: `await tester.pump(const Duration(milliseconds: 300))`.

**Observer rebuilds.** MobX rebuilds are asynchronous relative to the test, so pump between action and assertion.

```dart
// widget: Observer(builder: (_) => store.isLoading
//     ? const CircularProgressIndicator() : Text(store.displayName))
expect(find.text('Guest'), findsOneWidget);
unawaited(store.login('+15555550100'));
await tester.pump();                             // loading frame
expect(find.byType(CircularProgressIndicator), findsOneWidget);
await tester.pumpAndSettle();                    // resolved frame
expect(find.text('Test User'), findsOneWidget);
```

**Forms.** `enterText`, call `formKey.currentState!.validate()`, `pump()`, then assert on the error copy. Assert the error appears *and* that it goes away with a valid value — a validator that always fails passes the first half of that test.

## 6. Golden tests

A golden test renders a widget and compares pixels against a checked-in PNG: `expect(find.byType(PrimaryButton), matchesGoldenFile('goldens/primary_button.png'))`. `flutter test --update-goldens` rewrites the baselines.

**Use them for design-system components** — buttons, chips, badges, empty states, in their variants. **Not for whole screens.** A screen golden fails on every copy change, every date, every avatar; within a month someone is running `--update-goldens` reflexively without reading the diff, and the golden asserts nothing.

- Font rendering and antialiasing differ between a Linux CI runner and a macOS laptop, and the test environment substitutes a placeholder font unless you load real ones. **Generate goldens on one platform, gate on that platform only.**
- Stub anything non-deterministic — timestamps, random ids, network images — before the golden runs, and keep the count small. Ten to thirty for a design system is healthy; two hundred is a tax.
- `golden_toolkit` is discontinued. `alchemist` (Betterment / Very Good Ventures) is the maintained option when you want multi-device layouts and separate CI/local goldens. Plain `matchesGoldenFile` is enough to start.

Verified against https://pub.dev/packages/alchemist on 2026-09-07 — actively published, describes itself as heavily inspired by `golden_toolkit`.

## 7. Integration tests

```dart
// integration_test/login_flow_test.dart
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() => assertNotProductionTarget(
        const String.fromEnvironment('API_BASE_URL', defaultValue: ''),
      ));

  testWidgets('should reach home after a successful login', (tester) async {
    app.main();
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('phone_field')), '+15555550100');
    await tester.tap(find.text('Send Code'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('code_field')), '123456');
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle(const Duration(seconds: 5));

    expect(find.text('Home'), findsOneWidget);
  });
}
```

```bash
flutter test integration_test                                   # all specs, connected device
flutter test integration_test/login_flow_test.dart -d emulator-5554
flutter test integration_test --flavor dev --dart-define=API_BASE_URL=https://dev.example.com
```

Verified against https://docs.flutter.dev/testing/integration-tests on 2026-09-07 — `IntegrationTestWidgetsFlutterBinding.ensureInitialized()` and `flutter test integration_test/<file>.dart` are the documented shapes.

**Test accounts, not real ones.** Use a provider's reserved test phone numbers with fixed verification codes (Firebase Auth has a test-numbers list; SMS providers have sandbox numbers). Never a teammate's real phone. Use `+15555550100` in docs and examples — reserved fictional range, cannot be dialled.

**Never point an integration run at production.** In one of our projects a browser E2E run was aimed at production by a default env value; it created real rows and sent roughly ten real notifications to real people before anyone noticed. The "fix" was to point it back at DEV — a convention, not a guarantee. Make it a refusal instead:

```dart
// integration_test/support/prod_guard.dart
// Hosts that serve real users. Adding one here disables the suite against it
// forever. No override flag: enabling a production run is a reviewed edit to
// this list, not something set at 2am during a deploy.
const List<String> productionHosts = <String>['app.example.com'];

void assertNotProductionTarget(String baseUrl) {
  final host = Uri.tryParse(baseUrl)?.host.toLowerCase();
  // Fail closed: an unparseable or empty target is a refusal, not a pass.
  if (host == null || host.isEmpty) {
    throw StateError('Refusing to run: API_BASE_URL "$baseUrl" is not a URL.');
  }
  for (final prod in productionHosts) {
    // Hostname compare, never substring: contains('app.example.com') also
    // matches dev.app.example.com and would refuse every dev run — the fastest
    // way to get a safety guard deleted.
    if (host == prod || host.endsWith('.$prod')) {
      throw StateError('Refusing to run against production host "$host".');
    }
  }
}
```

The full version, including redirect following, is in [e2e-testing-guide.md](./e2e-testing-guide.md). `patrol` is worth a look when integration tests need native surfaces plain `integration_test` cannot touch — permission dialogs, the notification shade, WebViews, biometrics. Adopt it when you hit that wall, not before.

## 8. Device matrix reality

Decide the matrix once and write it into the repo, or every red starts an argument about whether it counts.

| Suite | Where | When | Wall clock |
|---|---|---|---|
| `flutter analyze`, `dart format --set-exit-if-changed` | Linux runner | Every push | seconds |
| Unit + widget (`flutter test --coverage`) | Linux runner, no device | Every push — this is the required check | 1-3 min |
| Golden | Linux runner (the platform that generated them) | Every push | seconds |
| Integration, Android | One emulator image, one API level | Nightly + pre-release | 10-25 min |
| Integration, iOS | One simulator on a macOS runner | Nightly + pre-release | 15-30 min, and the expensive line on the bill |
| Real devices (one old low-RAM Android, the current iPhone) | Device farm or a drawer | Release candidate only | manual |

- Only unit/widget/golden belong in the blocking PR check. Put integration on a schedule and a `release/*` trigger — a 25-minute required check is a check people learn to bypass. iOS needs a macOS runner, and hosted macOS minutes bill at a multiple of Linux minutes.
- Firebase Test Lab (or a similar farm) is the pragmatic real-device matrix: upload the app plus the test binary, get physical devices per run, no lab to maintain. Release-candidate lane, not per PR. Android emulator-in-CI works with a reusable AVD action, but without KVM on the runner it is slow enough to be useless.

```yaml
# .github/workflows/mobile-tests.yml
name: mobile-tests
on:
  push:
  pull_request:
  schedule:
    - cron: '0 3 * * *'
jobs:
  fast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with: { channel: stable, flutter-version: 3.24.0 }
      - run: flutter pub get
      - run: dart run build_runner build --delete-conflicting-outputs
      - run: dart format --set-exit-if-changed lib test
      - run: flutter analyze
      - run: flutter test --coverage --reporter expanded
  # Second job, same steps, `runs-on: macos-latest` (iOS has no other option),
  # gated on `if: github.event_name == 'schedule' ||
  #   startsWith(github.ref, 'refs/heads/release/')`, ending in:
  #   flutter test integration_test --flavor dev
  #     --dart-define=API_BASE_URL=https://dev.example.com
```

Verified against https://github.com/subosito/flutter-action on 2026-09-07 — `subosito/flutter-action@v2`, inputs `channel` and `flutter-version`.

## 9. Coverage

The floor is **80% on business logic** — `lib/stores/`, `lib/services/`, `lib/domain/`. Measure it on new code and ratchet: a PR may not lower the number. Never chase a global percentage.

UI coverage is not a goal. A widget file can hit 90% because one `pumpWidget` walked its `build` method and asserted nothing. That is the mobile version of fake coverage, and it is the single most common thing an AI agent produces when asked for "more coverage". A green number you cannot trust is worse than an honest gap. In review, grep the diff for tests with no `expect(`.

```bash
flutter test --coverage
# generated code otherwise inflates the number
lcov --remove coverage/lcov.info '*/*.g.dart' '*/*.freezed.dart' '*/*.mocks.dart' -o coverage/clean.info
genhtml coverage/clean.info -o coverage/html
```

## 10. Day 1 / Week 1 — greenfield

| When | Do |
|---|---|
| Day 1 | `flutter create --org com.example app_name`; set up `dev`/`prod` flavors before any feature code — retrofitting flavors into a shipped app is a lost day |
| Day 1 | Add the four dev dependencies. Write one trivially-true test, watch it pass, break it, watch it fail — prove the harness before you trust its verdict. Put the single-test command (`flutter test test/<path>_test.dart`) in the README |
| Day 1 | Stand up CI running format + `flutter analyze` + `flutter test` on every push, marked required the same day, while the suite is one test and nobody can object |
| Day 2-3 | First real unit test on a domain rule (pricing, a validator, a state transition), not a getter |
| Week 1 | Widget tests for design-system components as you build them: loading, disabled, error, empty. One integration test for the sign-in flow, behind the prod-guard, run nightly |
| Week 1 | Write `docs/testing.md`: commands, the matrix table above, coverage floor, mockito-or-mocktail |

## 11. Day 1 / Week 1 — existing app with zero tests

| When | Do |
|---|---|
| Day 1 | Get `flutter test` to run at all — it usually fails on missing generated files. Fix `build_runner`, commit that alone |
| Day 1 | Record the baseline in `docs/testing.md`: "`flutter analyze` reports 214 infos on a clean checkout — not your regression." A gate that fails on a known-red repo is uninstalled within a day |
| Day 1 | Adopt the rule before any backfill: if you fix a bug, write the test that would have caught it |
| Day 2 | Pick the store with the most bug tickets. If it reaches for GetIt internally, move the service to a constructor parameter — injectability is usually the only refactor you need — then write its first test |
| Day 3-5 | Characterization tests: assert what the store does *today*, wrong behaviour included, so refactors stop being silent. Fix the wrong ones afterwards, one commit each. Add format + analyze + test to CI as a required check at the current baseline — ratchet, never big-bang |
| Week 1 | Widget-test the two screens with the worst crash rate, starting with their loading and error states. Do not attempt integration tests yet — slowest to stabilise, least valuable while the unit layer is empty |

## 12. React Native notes

Same pyramid, different package names.

| Concern | Flutter | React Native |
|---|---|---|
| Runner / component tests | `flutter test`, `testWidgets` | `jest`, `@testing-library/react-native` `render` |
| Query priority | text > semantics label > type > key | `getByRole` / `getByText` > `getByLabelText` > `getByTestId` last |
| Interaction / settle | `tester.tap`, `enterText`, `pumpAndSettle` | `fireEvent.press`, `userEvent.type`, `waitFor` / `findBy*` |
| Mocks / golden | mockito or mocktail; `matchesGoldenFile` | `jest.mock` + MSW; `toMatchSnapshot` — same warning: components, not screens |
| E2E on device | `integration_test`, optionally patrol | Detox (grey-box, fast) or Maestro (YAML flows, easiest to start) |
| Coverage floor | 80% on stores/services | 80% on hooks/reducers/api layer |

The prod-guard applies unchanged: read the API base URL from test config, parse it, compare hostnames, refuse. No override flag.

---

## Sources & further reading

- Flutter testing, integration tests, coverage: https://docs.flutter.dev/testing · https://docs.flutter.dev/testing/integration-tests · https://docs.flutter.dev/testing/code-coverage
- Packages: https://pub.dev/packages/mockito (codegen) · https://pub.dev/packages/mocktail (no codegen) · https://pub.dev/packages/alchemist (goldens) · https://pub.dev/packages/patrol (native surfaces)
- `subosito/flutter-action` for GitHub Actions: https://github.com/subosito/flutter-action
- Michael Feathers, *Working Effectively with Legacy Code* — characterization tests, the technique behind the legacy table
- React Native: https://callstack.github.io/react-native-testing-library/ · https://wix.github.io/Detox/ · https://maestro.mobile.dev/

## Related

- [testing-from-zero.md](./testing-from-zero.md) — layers, the first-week plan, the test-smell catalogue
- [e2e-testing-guide.md](./e2e-testing-guide.md) — the full prod-guard design, including redirect following
- [enforcement/README.md](./enforcement/README.md) — turning these recommendations into instruction files, hooks and CI gates

_Last reviewed: 2026-09-07._
