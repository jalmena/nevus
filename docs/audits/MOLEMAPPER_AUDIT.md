# Audit: `ohsu-molemapper/MoleMapper_Final`

- Date: 2026-09-23
- Scope: the public MoleMapper iOS source release, audited as a candidate starting point for neVus.
- Method: read-only inspection through the GitHub API and the repository tarball at commit `4f3bd8a86da0760a82b32b1477600cfca8cd946d`. No build was attempted (no macOS/Xcode available) and no test suite exists to run. Line counts are raw lines, including comments and blanks.
- Paths are relative to the repository root and resolve as `https://github.com/ohsu-molemapper/MoleMapper_Final/blob/4f3bd8a86da0760a82b32b1477600cfca8cd946d/<path>`.

## Summary

MoleMapper_Final is an end-of-life source dump of an iOS-only application. Nothing in it (UIKit, Core Data, AVFoundation, a binary iOS build of OpenCV) can run in a browser or in Python. The parts worth carrying into a self-hosted web reimplementation are data and ideas: the 61-zone body taxonomy, the 32 zone polygons, the coin table, the tap-seeded auto-fit measurement algorithm (to port, not reuse) and the screen flow as a functional specification. Recommendation: clean reimplementation (option D) taking those components (option C). Recorded in [ADR-0002](../adr/0002-reimplement-instead-of-fork.md).

## 1. Repository facts

| Repository | Branch / HEAD | Commits | Created → last push | Notes |
| --- | --- | --- | --- | --- |
| `ohsu-molemapper/MoleMapper_Final` (audited) | `main` @ `4f3bd8a` | 1 | 2024-08-16 → 2024-10-02 | Description: "Public release of MoleMapper code without research components". 55 MB. |
| `ohsu-molemapper/MoleMapper_iOS_public` | `master` @ `d6253b1` | 2 (2017-07-25 "Published code", 2018-01-05 "3.0 Release") | 2017-07 → 2018-01 | Still contains the research layer (ResearchKit, Bridge, consent forms). |

Related repositories: the same organisation holds forks of ResearchKit, Bridge-iOS-SDK, CMSSupport, RNCryptor, ZipZap and ResearchStack. `ResearchStack/MoleMapperAndroid` is the Android port (Apache-2.0, last push 2019-07). `brian-bot/MoleMapper-sdata` holds the R scripts of the published paper.

- The single commit is `4f3bd8a` "Version 3.4 Source Code", 2024-08-16, by Tracy Petrie (OHSU). `git shortlog -sn` would list exactly one author.
- `git ls-remote` shows only `refs/heads/main`. No tags, no releases, no README, no CHANGELOG, no CI, no tests (zero XCTest references). 0 stars, 0 forks, 0 issues.
- Version: `MARKETING_VERSION = 3.4.0`, build 34/36 (`MoleMapper.xcodeproj/project.pbxproj` lines 2817, 2795, 3100).
- The project is dead. `Source/Learn More/RTF Files/support.rtf` says "the app is no longer in active development"; `Source/Learn More/RTF Files/WelcomeMessage.rtf` (line 8) says "we are no longer recruiting into the Mole Mapper Study … we won't be collecting additional data"; `Source/Onboarding/NewWelcome/NewWelcome.storyboard` (line 138) repeats it.
- App Store: the repository has no note about removal. Apple's lookup API showed the app still listed on 2026-09-23: "Mole Mapper Melanoma Study", bundle `org.sagebase.molemapper`, v3.4.0, released 2022-12-28, minimum iOS 12.0, seller "Oregon Health & Science University Apps" (`apps.apple.com/us/app/id1048337814`).
- The old repository's README says the code was "authored and originally developed by Dan Webster".

## 2. Licence

### `License.md`

`License.md` is byte-identical in both repositories. It is a BSD-3-Clause licence, "Copyright (c) 2015, Oregon Health and Science University", with a drafting defect: clause 3 was copied from the BridgeSDK licence and names Sage Bionetworks and "BridgeSDk's contributors" instead of OHSU. GitHub therefore cannot classify it and reports `NOASSERTION`. The verbatim text is reproduced in [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).

### Per-file headers

About 177 source files carry a clean BSD-3 header, for example `MoleMapper/Supporting Files/MoleMapper-Bridging-Header.h` lines 4–30, "Copyright (c) 2017-2022 OHSU". Its clause 3 adds an explicit trademark carve-out:

```text
// 3.  Neither the name of the copyright holder(s) nor the names of any contributors
// may be used to endorse or promote products derived from this software without
// specific prior written permission. No license is granted to the trademarks of
// the copyright holders even if such marks are included in this software.
```

First-party copyright variants (file counts): `(c) 2018 OHSU` (49), `(c) 2017-2022 OHSU` (46), `(c) 2016, OHSU` (46), `(c) 2016, 2017 OHSU` (21), `(c) 2022, OHSU` (7), `© 2018 OHSU` (5), `(c) 2017, OHSU` (2), `© 2019 OHSU` (1), `© 2019 Tracy Petrie. All rights reserved.` (1, `Source/Onboarding/NewWelcome/AppOnboardingViewController.swift` line 6). Named authors: Dan Webster, Tracy Petrie, Luis Escamilla, Alejandro Cárdenas; the acknowledgements also credit "Unosquare for help with coding".

Ten files carry a copyright line but no licence grant: `AppOnboardingViewController.swift`, `Settings/Reminder Frequency/ReminderFrequencyViewController.swift`, `ReviewPhoto/ZoomAreaView.swift`, three files under `Source/DevOnly/`, `Dashboard/Views/Libraries/UAProgressView.{h,m}` and `Dashboard/Views/TableView Cells/DashboardActivityCompletionCell.{h,m}`.

### Other licence and notice files

- `Source/Learn More/RTF Files/license.rtf`: the in-app notices. Stale: they list Alamofire, BridgeSDK (with UICKeyChainStore and Reachability), Instructions, OpenCV, ResearchKit, ZipZap and Freepik; several are no longer in the repository, while Charts and the YouTube player helper, which are, go unlisted.
- `Source/Learn More/RTF Files/acknowledgements.rtf`.
- `Pods/Instructions/LICENSE` (MIT), `Pods/NSString-Hashes/LICENSE` (public domain), `Pods/Target Support Files/*/…-acknowledgements.{markdown,plist}`.

### Third-party code in the repository

| Component | Location | Licence |
| --- | --- | --- |
| OpenCV 3.2.0 | `opencv2.framework` (72.5 MB binary + 96 headers) | BSD-3 (Intel, Willow Garage, OpenCV Foundation, Itseez, NVIDIA, AMD, Google) |
| Charts (danielgindi port, 2015) | `Charts/` (83 Swift files) | Apache-2.0. Not compiled: zero references in the Xcode project |
| Instructions 1.2.2 | `Pods/Instructions` | MIT (Frédéric Maquin) |
| NSString-Hashes 1.2.2 | `Pods/` | Public domain |
| YouTube iOS player helper | `Source/Common/Helpers/{WK,}YTPlayerView.*` | Apache-2.0 (Google 2014). Unused |
| QTouchposeApplication | `Source/AppDelegate/` | Apache-2.0 (Todd Reed). Only used by the "Mov" target |
| AppCore fragments | `ThirdParty/APC/*`, `UIAlertController+Helper.*` | BSD-3 "Copyright (c) 2015, Apple Inc." |
| AVCam-derived capture code | `Source/Common/MMPhoto/PreviewView.swift` lines 1–3 ("See LICENSE.txt…", file not included); `TakePhotoViewController.swift` lines 35–38 | Apple sample-code licence |
| UAProgressView | `Source/Dashboard/Views/Libraries/` | "© 2014 Urban Apps. All rights reserved", no licence text |
| DashboardActivityCompletionCell | `Source/Dashboard/…` | "UCSF Pride … © 2015 Analog Republic. All rights reserved", no licence grant |
| CMPopTipView, OBShapedButton, UIImage+ColorAtPixel | `ThirdParty/Common` | MIT (Chris Miles; Ole Begemann) |
| SMCalloutView 2.1.5 | `ThirdParty/Common` | No licence text; embeds Nick Lockwood's Base64 code under zlib (`SMCalloutView.m` lines 716–745) |
| UIImage+Resize / Alpha / RoundedCorner / Extras | `ThirdParty/Common` | Trevor Harmon, "Free for personal or commercial use" |

### Image and asset licensing

- No licence statement specific to assets exists. `License.md` covers the software "in source and binary forms".
- The acknowledgements credit "Freepik icons hosted on flaticon.com" and "Images from pexels.com"; `license.rtf` ends with "Icons by Freepik…". Those assets are under their own licences, not BSD. Which files are Freepik is not stated; the Pixelmator-edited `stethoscope-medical-tool-outlineshadow.png` and `microscope-dropshadow.png` used in onboarding look like Freepik icons (inference).
- The body-map PNGs carry no third-party attribution and no author or rights metadata (the XMP only says `Adobe ImageReady`). They are most likely OHSU-made, but that is not explicit.

### Trademarks

"MoleMapper™" appears in `WelcomeMessage.rtf` and `acknowledgements.rtf`; "War on Melanoma™" in `Source/Learn More/LearnMoreWorker.swift` lines 53–54 and `NewWelcome.storyboard` line 204. Bundled logos: `ohsuLogoSquare`, `ohsuLogoTVC`, `ohsuSageLogos` (OHSU + Sage), `researchKit` (Apple's ResearchKit logo), `moleMapperLogo` and the app icons. The per-file clause grants no trademark licence.

### Consent and IRB material

- Final repository: `MoleMapper/Supporting Files/privacyPolicy_2016_05_27.pdf`, the three-page study privacy policy (Synapse storage, disclosure to NCI and OHRP, link to `syn2502577`).
- Old repository, under `MoleMapper/interfaceTesting/`: `consentForm_16038_2016_05_27.html`, `16038_10561_Consents.{html,pdf}`, `16038_Consent_ex2018_04_13.pdf`, `10561_Consent_ex2017-12-28.pdf`, `10561_Consent_ex2018-12-17.pdf`, `WarOnMelanoma_InformationSheet_2014June06.pdf`, `WoM-Information.Sheet.revisions.TRACKED_2015_10_09.pdf`, `helpOurResearch.htm`.
- IRB 16038 is Mole Mapper (PI Sancy Leachman MD PhD; co-investigators Cassidy, Petrie, Webster, Samatham; funded by OHSU Dermatology and the Knight Cancer Institute). IRB 10561 is the Melanoma Community Registry.

## 3. Architecture

### Lines of code

| Area | Files | Lines | Notes |
| --- | --- | --- | --- |
| `Source/` Swift | 128 | 17,959 | First-party |
| `Source/` Objective-C `.m` / `.h` / `.mm` | 26 / 28 / 1 | 7,484 / 2,689 / 454 | Includes about 4.3k lines of embedded third-party code (YouTube helpers ~3.4k, UAProgressView, QTouchpose) |
| `Source/` XIB + storyboards | 34 | 2,918 | |
| `Source/` RTF / HTML / strings / Core Data models | 21 | 709 | |
| `ThirdParty/` Objective-C | 26 | 4,384 | |
| `Pods/` | 95 | 8,214 | |
| `Charts/` | 85 | 18,447 | Dead code |
| `opencv2.framework` headers | 97 | 60,316 | Plus the 72.5 MB binary |

Roughly 5k lines of the first-party code are the 30-line licence header repeated in about 177 files (estimate). Large binaries: three tutorial MP4s (16.9 MB), three onboarding illustrations at 1862×1080 (about 27 MB, apparently unreferenced) and three body-map PNGs (1.2 MB).

### Xcode setup

- `MoleMapper.xcworkspace` contains `MoleMapper.xcodeproj` and `Pods/Pods.xcodeproj`. Project format `objectVersion = 46`, `LastUpgradeCheck = 1340`.
- Three targets (pbxproj lines 1843–1895): `MoleMapper` (Swift 5.0), `MoleMapper Dev` (Swift 4.2, `-DDEBUG`, adds a "Dev Only" tab; `MainTabBarController.swift` lines 42–51) and `MoleMapper Mov` (Swift 4.2, `-D TOUCHPOSE`, touch visualisation; uses `MoleMapper copy-Info.plist`, which contains a Fabric API key at line 32).
- Deployment target iOS 12.0 in all eight configurations; the Podfile says `platform :ios, '10.0'` (inconsistent). iPhone only, portrait only, light mode only (`MoleMapper-Info.plist` lines 54–59). All targets use bundle ID `org.sagebase.molemapper`.
- Swift and Objective-C are joined via `MoleMapper-Bridging-Header.h`. The capture/measure screens use a "Clean Swift" scene pattern (Interactor / Presenter / Router / Worker / Models; see `CoinUsedRouter.swift` line 34). The older parts (Dashboard, body-map drawing) are Objective-C MVC.

### Screens and flow

1. Launch: welcome carousel on first run, otherwise the body map (`AppDelegate.swift` lines 69–81). Carousel pages: "Welcome to MoleMapper!", "Show Your Doctor", "MoleMapper Research" (study closed, link to War on Melanoma), "Start mapping!".
2. Tabs: Mole Map, Dashboard, Learn More (`MainTabBarController.swift` lines 38–73).
3. Body map (`Source/BodyMapVCs/BodyMapViewController.swift`): front/back flip and a head-detail overlay; zones are shaped buttons with red badges when moles are due for re-measurement; tutorial coach marks (Instructions library), local video tutorials (lines 297–308), Settings entry (lines 259–261).
4. Tapping a zone (`MeasurementController.swift` lines 46–63): new zone → TakePhoto with the torch on (`TakePhotoViewController.swift` lines 270–282); existing zone → ShowZone (mole pins on the last photo; rename / history / delete; "Photograph Zone").
5. Capture chain: TakePhoto → ReviewPhoto (zoom rectangle to check blur; Use / Retake) → CoinUsed ("Did you include an (optional) coin in your photo?") → IdentifyCoin → IdentifyMoles → save. On re-measurement the camera overlays the pins of the previous session to help alignment (`RepeatZonePhoto.rtf`).
6. ReviewMoles shows each mole's history (swipe or cross-fade between measurements) and can email the images to a doctor (`ReviewMolesInteractor.swift` lines 95–141).
7. Dashboard (Objective-C): zones documented, moles re-measured this month, biggest and average mole, size change over time.
8. Settings: help and hints toggles, notifications, reminder frequency. Reminders use `UNUserNotifications` plus an optional calendar event (`NotificationsManager.swift` lines 151–230).

The research features are absent in the Final release: no ResearchKit consent, no surveys, no Bridge upload. Leftovers: `//import ResearchKit` (`BodyMapViewController.swift` line 39), "Encapsulated data to ship to Bridge" (`FixableData.swift` line 58), the `uploadSuccess` attribute, a commented-out `bridgeManager` (`DashboardModel.m` lines 331–336). They all live in the old repository.

### Data model

Core Data model `Version30.xcdatamodeld`, current version `Version31`, loaded via `NSPersistentContainer` (`Source/CoreData/V30Stack.swift` lines 56–65):

| Entity | Attributes | Relationships |
| --- | --- | --- |
| User | mmUserID | zones ↔ Zone30 (to-many) |
| Zone30 | zoneID (String) | moles (to-many), zoneMeasurements (to-many), whichUser |
| Mole30 | moleID (UUID string), moleName, moleWasRemoved, waitingForResults | moleMeasurements (cascade), whichZone |
| ZoneMeasurement30 (one photo session) | zoneMeasurementID, date, fullsizePhotoFilename, displayPhotoFilename, referenceObject (Int16: 0/1/5/10/25), referenceX/Y, referenceDiameterInPoints, referenceDiameterInMillimeters, lensPosition, gravityX/Y/Z, uploadSuccess | moleMeasurements (cascade), whichZone |
| MoleMeasurement30 | moleMeasurementID, date, moleMeasurementX/Y, moleMeasurementDiameterInPoints, calculatedMoleDiameter (mm, −1 if unknown), calculatedSizeBasis, moleMeasurementPhoto | whichMole, whichZoneMeasurement |

There is also `News.xcdatamodeld` (a Story entity) and a legacy v2.x `InterfaceTesting.xcdatamodeld` (Zone / Mole / Measurement); the v2 migration code was removed. Photos are files in the app's Documents folder: `full<UUID>.jpg` (full resolution) and `display<UUID>.png` (screen-sized) (`ZoneMeasurement30+CoreDataClass.swift` lines 85–134), plus a 320×320 crop per mole `mole<UUID>.jpg` (`MoleMeasurement30+CoreDataClass.swift` lines 52–62). Coordinates are stored in display-image points, not full-resolution pixels.

### Body map representation

- Backgrounds are raster: `bodyFrontInnerLines_v03.png`, `bodyBackInnerLines_v03.png` and `headDetail.png`, each 1512×2828 RGBA, exactly 7× a 216×404-point drawing area (`VariableStore.m` lines 64–65).
- The zones are vector data in code: 32 straight-line polygons (moveTo/lineTo) in `Source/Common/Helpers/VariableStore.m` lines 319–812, placed at per-zone origins in `BodyFrontView.m` lines 60–101, `BodyBackView.m` lines 53–94 and `HeadDetailView.m` lines 64–78. They become paths (`BaseZone.m` lines 61–79) and filled images (0.4 alpha when highlighted, 0.5 white without a photo, 0.01 with one; `BaseZone.m` lines 82–117). Hit-testing uses the alpha of those images (OBShapedButton).
- Shape IDs: 10, 15, 17, 40, 45, 50, 55, 60, 300, 301, 650, 651, 700, 701, 750, 751, 800, 801, 850, 851, 1200, 1250, 1251, 1350, 1351, 1400, 1401, 2200, 2250, 2251, 2350, 2351.

### Zone taxonomy

61 IDs, exactly as in `Source/CoreData/Zone30+CoreDataClass.swift` lines 460–539:

| Front | Back |
| --- | --- |
| 1100 Head (opens head detail) | 2100 Head (opens head detail) |
| 1200 Neck & Center Chest | 2200 Neck |
| 1250 Right Pectoral / 1251 Left Pectoral | 2250 Left Upper Back / 2251 Right Upper Back |
| 1300 Right Abdomen / 1301 Left Abdomen | 2300 Left Lower Back / 2301 Right Lower Back |
| 1350 Right Pelvis / 1351 Left Pelvis | 2350 Left Glute / 2351 Right Glute |
| 1400 Right Upper Thigh / 1401 Left Upper Thigh | 2400 Left Upper Thigh / 2401 Right Upper Thigh |
| 1450 Right Lower Thigh & Knee / 1451 Left Lower Thigh & Knee | 2450 Left Lower Thigh & Knee / 2451 Right Lower Thigh & Knee |
| 1500 Right Upper Calf / 1501 Left Upper Calf | 2500 Left Upper Calf / 2501 Right Upper Calf |
| 1550 Right Lower Calf / 1551 Left Lower Calf | 2550 Left Lower Calf / 2551 Right Lower Calf |
| 1600 Right Ankle & Foot / 1601 Left Ankle & Foot | 2600 Left Ankle & Foot / 2601 Right Ankle & Foot |
| 1650 Right Shoulder / 1651 Left Shoulder | 2650 Left Shoulder / 2651 Right Shoulder |
| 1700 Right Upper Arm / 1701 Left Upper Arm | 2700 Left Upper Arm / 2701 Right Upper Arm |
| 1750 Right Upper Forearm / 1751 Left Upper Forearm | 2750 Left Elbow / 2751 Right Elbow |
| 1800 Right Lower Forearm / 1801 Left Lower Forearm | 2800 Left Lower Forearm / 2801 Right Lower Forearm |
| 1850 Right Hand / 1851 Left Hand | 2850 Left Hand / 2851 Right Hand |

Head detail: 3150 Face: Left Side, 3151 Face: Right Side, 3170 Top of Head, 3171 Face: Front, 3172 Back of Head.

The last digit (0/1) means screen-left vs screen-right, while names are from the patient's point of view: on the front view ID `…0` is the patient's right; on the back view `…0` is the patient's left. 1100 and 2100 never store photos; they roll up the 31xx head zones (`Zone30+CoreDataClass.swift` lines 225–241).

## 4. Measurement algorithm

Semi-automatic: the user taps, the app auto-fits a circle, and the user can then correct it. A coin is the size reference. OpenCV is used for basic image processing only; there is no Hough transform and no contour fitting.

1. **Capture** (`TakePhotoViewController.swift` lines 341–358; `TakePhotoCaptureDelegate.swift` lines 59–77): a full-resolution JPEG plus a preview image sized to `UIScreen.main.bounds` (screen points, e.g. 375×667). All measuring happens on the small preview image. Lens position and gravity vector are recorded but never used for sizing (the Info.plist says motion data "will eventually help us to remove the coin step"). Help text tells users to hold the phone "about two fists distance from skin".
2. **Coin:** the user taps the coin, creating a circle of radius 30 defaulting to a penny (`IdentifyCoinInteractor.swift` lines 96–107). `AutoEncircle.autoEncircleCoin` (`Source/Common/OpenCVWrapper/Autosize.swift` lines 223–266) runs the generic routine twice with "shiny" and "dark" settings, keeps candidates with radius 12–55 px, scores each by squared distance from the tap divided by circle fill ratio, and falls back to the tap point with radius 25 if none qualifies. A result whose centre moved more than max(48, r) from the tap is discarded (`IdentifySharedWorker.swift` lines 219–227). The user picks the denomination and can drag or pinch the circle (`CircleWidget.swift` lines 108–110, 295–311).
3. **Generic routine** (`Autosize.swift` lines 286–350 plus `OpenCVWrapper.mm`): take one colour channel, Gaussian-blur it, apply an adaptive threshold (`OpenCVWrapper.mm` lines 140–160); label connected components and drop any wider or taller than 105 px to remove edges (lines 407–452); small 7×7 open to remove hairs, larger close to bridge reflections; pick the region nearest the tap and return its minimum enclosing circle (lines 349–405).

   | Settings | Channel | Blur kernel / sigma | Threshold block / offset / polarity | Dilate / erode | Radius limits |
   | --- | --- | --- | --- | --- | --- |
   | Mole | red | 7 / 2.5 | 39 / 5 / inverted | 9 / 11 | clamped 5–80 px |
   | Dark coin | red | 11 / 3.5 | 55 / 10 / inverted | 23 / 25 | 12–55 px |
   | Shiny coin | blue | 5 / 2.0 | 65 / −16 / normal | 21 / 21 | 12–55 px |

4. **Moles** (`IdentifyMolesInteractor.swift` lines 224–255, 331–336): a tap creates a circle of radius 20 and auto-fits it with the mole settings. On re-measurement, a fit that moves more than max(48, r) or changes radius by more than ±20 % is rejected and the mole is flagged "existing, not confident" (`IdentifySharedWorker.swift` lines 86–91, 230–235). Any mole circle can be turned into the coin ("Mark as coin"). Names are auto-generated (`MoleNameGenerator.m`).
5. **Size:** `coinDiametersInMillemeters = [0:0, 1:19.05, 5:21.21, 10:17.91, 25:24.26]` (`TranslateUtils.swift` line 53): US penny, nickel, dime and quarter. mm per pixel = coin mm ÷ coin diameter in pixels; mole mm = 2 × mole radius in pixels × mm per pixel (`IdentifyMolesInteractor.swift` lines 325–329; `IdentifyMolesWorker.swift` lines 172–229). Without a coin the size is stored as −1. The enum is misspelled `nickle` (`ObjectPosition.swift` lines 51–75).
6. **Saving:** one photo session per zone, a mole record per mole, and a crop of 4× the mole radius from the full JPEG, resized to 320 px (`TranslateUtils.swift` lines 238–254).

Uncertainty is not handled: no error estimate, no perspective, tilt or lens correction; the coin is assumed coplanar with the moles; sizes are shown to 0.1 mm (`ReviewMolesInteractor.swift` lines 102–121). At the accepted coin sizes one preview pixel is roughly 0.17–0.79 mm, so a one-pixel radius error moves a mole's size by about 0.35–1.6 mm (estimate). A field meant to record how the size was derived is always overwritten (`IdentifyMolesWorker.swift` lines 217–225):

```swift
if (mmPerPixel > 0) {
    moleMeasurement30.calculatedMoleDiameter = NSNumber(value: (Float(position.radius) * 2) * mmPerPixel)
    moleMeasurement30.calculatedSizeBasis = 1
} else {
    moleMeasurement30.calculatedMoleDiameter = -1.0
    moleMeasurement30.calculatedSizeBasis = 0
}

moleMeasurement30.calculatedSizeBasis = 0
```

Neither repository contains any validation of the measurements.

## 5. Dependencies

| Dependency | Version in repo | Upstream status (2026-09-23) | Notes |
| --- | --- | --- | --- |
| OpenCV (vendored binary) | 3.2.0 | Latest release 5.0.0 (2026-06) | Old-style multi-architecture file (armv7, armv7s, i386, x86_64, arm64), not an XCFramework, no Apple-silicon simulator build; 72 MB committed |
| Instructions (CocoaPods, `Pods/` committed) | 1.2.2 (CocoaPods 1.11.3) | Upstream 2.3.0 | Coach marks in five screens |
| NSString-Hashes | 1.2.2 | — | Linked, no call sites found |
| Charts, YouTube helper, AppCore bits, misc UI helpers | vendored source | AppCore archived (2019) | Charts and YouTube helper are dead code |
| Submodules / Carthage / SPM | none in Final | — | Old repo: `.gitmodules` points at Sage-Bionetworks/Bridge-iOS-SDK, archived 2023-06 |
| Old repo pods | AFNetworking 2.5.4, ResearchKit 1.2.1, zipzap 8.0.4, KLCPopup HEAD | ResearchKit upstream still active; the rest long obsolete | — |

## 6. Reusable components for neVus

Ratings: (a) reuse as-is, (b) port as algorithm/concept, (c) reference only, (d) obsolete.

| Candidate | Rating | Why |
| --- | --- | --- |
| Zone taxonomy (61 IDs and names) | (a) | Plain data under BSD-3. Export to JSON with explicit side and view fields, since the ID digit does not encode anatomical side |
| Zone polygons (`VariableStore.m` + per-view origins) | (a)/(b) | Straight-line polygons on a 216×404 grid; a small script can generate SVG from them. Keep the OHSU notice |
| Body-map artwork (three PNGs) | (c) | Raster only, no vector source, no attribution, rights not explicit. Redraw as SVG or obtain written confirmation from OHSU |
| Coin/mole auto-fit (`Autosize.swift` + `OpenCVWrapper.mm`, ~350 lines) | (b) | Maps directly onto Python OpenCV calls. Pixel settings must be rescaled for full-resolution images and given an error estimate |
| Measurement approach and coin table | (b) / (a) | Tap to seed, auto-fit, user corrects. Add non-US coins and an uncertainty estimate |
| Data model | (b) | Zone → photo session → mole measurement ← mole is a sound shape. Move to SQL with explicit units, resolution and method fields |
| Screen flow (capture → blur check → coin? → coin → moles; alignment pins; history slider; share with doctor; reminders) | (b) | A good functional specification; the UIKit code itself is not reusable |
| Help texts (`PopupHelp/Help Files/*.rtf`), disclaimer (`support.rtf`) | (b) | Short BSD-licensed text; rewrite freely |
| Onboarding text, tutorial videos, logos | (c) | Tied to the closed study and OHSU / War on Melanoma branding |
| Surveys (old repo: `InitialSurveyRKModule.m`, `MoleWasRemovedRKModule.m`, `RemovedMoleHelper.m`) | (c) | Short question sets tied to IRB 16038 and ResearchKit |
| Consent, privacy and IRB documents; Bridge / AppCore upload and encryption; REDCap export (`DataExporter.m`) | (d) | Study-specific legal material and dead services |
| Freepik/Pexels icons and images | (d) | Separate licences; replace |
| Mole name list (`MoleNameGenerator.m`) | (a) | BSD; a fun extra |
| Measurement validation documentation | none | Not in either repository; the only source is the 2017 paper |

## 7. Technical debt and obsolescence

- Toolchain: iOS 12 target; mixed Swift 4.2/5.0; 2013-era project format; OpenCV 3.2 binary that will not build for Apple-silicon simulators; hard-coded OpenCV stats-array width ("for 3.0; somewhere by 3.3 it became 6", `OpenCVWrapper.mm` line 38); label images round-tripped through `UIImage` with "iOS 12 fix" bit masks; `-finalize` never called under ARC so C buffers leak (`OpenCVWrapper.mm` lines 70–75).
- Deprecated APIs: `statusBarFrame` (8 uses), the sample-buffer photo capture API deprecated since iOS 11 (`TakePhotoCaptureDelegate.swift` lines 59–65), `isHighResolutionPhotoEnabled`, `UIGraphicsBeginImageContext`, `keyWindow`, `openURL:`.
- Configuration and security: arbitrary HTTP loads allowed (`MoleMapper-Info.plist` lines 29–33); `armv7` still a required device capability; a Fabric/Crashlytics API key committed in `MoleMapper copy-Info.plist` line 32 (Fabric itself is retired); bundle ID in Sage's namespace; the War on Melanoma link is plain `http://` (`AppDelegate.swift` line 98).
- Bugs: the size-basis overwrite (section 4); `referenceDiameterInMillimeters` left as a TODO (`IdentifyMolesWorker.swift` lines 166–167); email attachments all named `image0.jpg` (`ReviewMolesInteractor.swift` lines 110–112); horizontal margin computed from the view's height (`IdentifySharedWorker.swift` line 158); `fatalError` on Core Data save errors (`V30Stack.swift` lines 71–82).
- Dead weight: Charts (18.4k lines, never compiled), the YouTube helper, `ReferenceConverter`, CMPopTipView, ScaledImageView, CustomCrossFadeSegue; about 36 of 73 image sets appear unreferenced; a missing `transparent360x360.png` referenced at `BaseZone.m` line 85; no tests of any kind.
- Cloud and platform: the Final app is local-only; its only export is email. The research back-ends in the old repository (Sage Bridge study `ohsu-molemapper`, REDCap, Synapse) are archived or closed. None of the code can run in a browser or in Python.

## 8. Migration options

- **(A) Direct fork: not recommended.** 0 % reusable code for a PWA or Python backend, plus dead code, the malformed licence clause, Freepik icons and OHSU/Sage trademarks and identifiers.
- **(B) Fork plus progressive rewrite: not feasible.** There is no shared runtime to migrate UIKit/Core Data piece by piece into TypeScript/Python.
- **(C) Partial reuse: low risk, modest gain.** Port the zone taxonomy and polygons to JSON/SVG, the coin table and the auto-fit algorithm (about 350 lines) to Python OpenCV with tests. Keep the BSD notice (OHSU 2015–2022).
- **(D) Clean reimplementation inspired by MoleMapper: recommended, combined with (C).** Use MoleMapper as the functional specification (zones, sessions, the coin step, auto-fit-then-correct, alignment pins, history view, reminders); design from day one what it lacks (measurement on full-resolution images, uncertainty, tilt/perspective checks, non-US references, export, multi-user self-hosting); use a different name, new artwork and none of the consent or study material.

## 9. Publications, datasets and study documentation

- The iOS repositories contain no DOI or paper citation. Study documents: the privacy policy (both repos, Synapse governance `syn2502577`) and the IRB 16038/10561 consent forms and War on Melanoma sheets (old repo only). Upload schemas (old repo): `initialData.json` fields autoImmune, birthyear, eyeColor, familyHistory, gender, hairColor, immunocompromised, melanomaDiagnosis, moleRemoved, profession, shortenedZip (`InitialSurveyRKModule.m` lines 234–248); archives `coreAttributes` (revision 3), `moleMeasurement`, `removedMole` (revision 2), `userFeedback` (`BridgeManager.m` lines 621–736). A calibration flow sent coin photos taken close, mid and far, with lens positions, to Bridge; the regression model it was meant to feed was never written (`CalibrationController.swift` lines 155–202).
- Paper: Webster DE, Suver C, Doerr M, Mounts E, Domenico L, Petrie T, Leachman SA, Trister AD, Bot BM. "The Mole Mapper Study, mobile phone skin imaging and melanoma risk data collected using ResearchKit." *Scientific Data* 4:170005 (2017), doi:10.1038/sdata.2017.5, CC BY 4.0.
- Dataset (from `brian-bot/MoleMapper-sdata`): Synapse project `syn5576734`; controlled-access tables `syn6829807`–`syn6829810`, `syn6829811` with its own restriction (probably the images; not verified); `syn6829807` is the demographics table. A second release (Petrie et al., *Scientific Data* 2025) is at `syn51520810`; see the landscape research for its terms.

## Key takeaways

- The exact repository exists: one 2024 commit, no README, tags or tests, abandoned since. The app is still listed on the App Store.
- BSD-3 (OHSU), but `License.md` clause 3 names Sage/BridgeSDK instead of OHSU. The per-file headers are correct and reserve all trademarks.
- The research layer exists only in the older `MoleMapper_iOS_public` repository, with IRB documents.
- Some icons and images are Freepik/Pexels; OHSU, Sage and ResearchKit logos are bundled; the body-map PNGs have no explicit licence or attribution.
- The body map is raster art plus 32 vector polygons in code, convertible straight to SVG. The 61-zone taxonomy is directly reusable.
- Measurement is tap-seeded auto-fitting in OpenCV with drag/pinch correction and US coins as reference, computed on a screen-sized preview with no error handling.
- OpenCV 3.2 is a 72 MB pre-XCFramework binary; Charts and the YouTube helper are dead code; a Fabric API key is committed.
- No part of the code can run in a browser or in Python.
- Recommendation: clean web reimplementation, porting the zone data, polygons, coin table and auto-fit algorithm with the OHSU notice kept, and a data model that carries resolution and uncertainty.
