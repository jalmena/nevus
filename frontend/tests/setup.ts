import "fake-indexeddb/auto";
import "@testing-library/jest-dom/vitest";
import "@/lib/i18n";

import { configure } from "@testing-library/react";

// The default second for findBy* is short once many test files run at once on a loaded machine or a
// small CI runner; a wait that ends early only makes a test flaky, never more correct.
configure({ asyncUtilTimeout: 5000 });
