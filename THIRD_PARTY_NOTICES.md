# Third-party notices

neVus is licensed under the GNU Affero General Public License, version 3.0 only (see [LICENSE](LICENSE)). This file lists third-party material that neVus incorporates, ports or derives from, together with the notices their licences require. Every entry names what was taken and where it lives in this repository. The file grows as components are added.

## MoleMapper (Oregon Health & Science University)

neVus is inspired by MoleMapper, the iOS application released by OHSU. The following components are ported from `ohsu-molemapper/MoleMapper_Final` at commit `4f3bd8a86da0760a82b32b1477600cfca8cd946d` (see [ADR-0002](docs/adr/0002-reimplement-instead-of-fork.md)); each line will point at its location in this repository once the port lands:

| Component | Origin in MoleMapper | Location in neVus |
| --- | --- | --- |
| 61-zone body taxonomy (identifiers and names) | `Source/CoreData/Zone30+CoreDataClass.swift` | planned (body-map data) |
| 32 zone polygons and their per-view origins | `Source/Common/Helpers/VariableStore.m`, `BodyFrontView.m`, `BodyBackView.m`, `HeadDetailView.m` | planned (generated SVG regions) |
| Reference-coin diameter table | `Source/Common/Helpers/TranslateUtils.swift` | planned (scale references) |
| Tap-seeded auto-fit measurement algorithm (structure) | `Source/Common/OpenCVWrapper/Autosize.swift`, `OpenCVWrapper.mm` | planned (Python reimplementation) |

No MoleMapper artwork, logos, names, onboarding text, consent material or study material is used. "MoleMapper" and "War on Melanoma" are trademarks of their owners; no trademark licence is granted or claimed. neVus is not affiliated with or endorsed by OHSU, Sage Bionetworks or the MoleMapper study.

MoleMapper is distributed under the BSD 3-Clause licence. Two forms of the notice appear in the original repository and both are reproduced verbatim below: the repository licence file (whose third clause names Sage Bionetworks and BridgeSDK contributors, a drafting defect of the original) and the per-file source header (which names the copyright holders correctly and reserves their trademarks).

### Repository licence file (`License.md`)

```text
MoleMapper for iOS is available under the BSD license:

	Copyright (c) 2015, Oregon Health and Science University
	All rights reserved.

	Redistribution and use in source and binary forms, with or without
	modification, are permitted provided that the following conditions are met:
	    * Redistributions of source code must retain the above copyright
	      notice, this list of conditions and the following disclaimer.
	    * Redistributions in binary form must reproduce the above copyright
	      notice, this list of conditions and the following disclaimer in the
	      documentation and/or other materials provided with the distribution.
	    * Neither the name of Sage Bionetworks nor the names of BridgeSDk's
		  contributors may be used to endorse or promote products derived from
		  this software without specific prior written permission.

	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
	ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
	WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
	DISCLAIMED. IN NO EVENT SHALL OREGON HEALTH AND SCIENCE UNIVERSITY BE LIABLE FOR ANY
	DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
	(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
	LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
	ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
	(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
	SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### Per-file source header (`MoleMapper/Supporting Files/MoleMapper-Bridging-Header.h`, lines 1–31)

```text
//
// MoleMapper
//
// Copyright (c) 2017-2022 OHSU. All rights reserved.
//
// Redistribution and use in source and binary forms, with or without modification,
// are permitted provided that the following conditions are met:
//
// 1.  Redistributions of source code must retain the above copyright notice, this
// list of conditions and the following disclaimer.
//
// 2.  Redistributions in binary form must reproduce the above copyright notice,
// this list of conditions and the following disclaimer in the documentation and/or
// other materials provided with the distribution.
//
// 3.  Neither the name of the copyright holder(s) nor the names of any contributors
// may be used to endorse or promote products derived from this software without
// specific prior written permission. No license is granted to the trademarks of
// the copyright holders even if such marks are included in this software.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//
```

## Typefaces

The brand assets under `docs/design/brand/identity/` contain glyph outlines derived from the typefaces below, and the interface ships their font files self-hosted. Both are licensed under the SIL Open Font License, Version 1.1; the licence texts are kept next to the assets.

| Typeface | Copyright | Licence | Use |
| --- | --- | --- | --- |
| B612 | Copyright 2012 The B612 Project Authors (https://github.com/polarsys/b612) | SIL OFL 1.1 ([`docs/design/brand/identity/licences/OFL-B612.txt`](docs/design/brand/identity/licences/OFL-B612.txt)) | wordmark outlines |
| Epilogue | Copyright 2020 The Epilogue Project Authors (https://github.com/Etcetera-Type-Co/Epilogue) | SIL OFL 1.1 ([`docs/design/brand/identity/licences/OFL-Epilogue.txt`](docs/design/brand/identity/licences/OFL-Epilogue.txt)) | interface and report typeface; tagline outlines |
