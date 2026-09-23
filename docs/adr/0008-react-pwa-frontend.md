# ADR-0008: React progressive web application with a token-based design system

- Status: Accepted
- Date: 2026-09-23
- Deciders: engineering

## Context

The interface is mobile-first (a phone in front of a mirror) and must also work on a desktop; it needs an interactive SVG body map with touch gestures, camera capture flows, canvas-based image comparison, charts, an offline capture queue, two interface languages from the first release, and accessibility from the start. The Product Owner asked for a coherent design system rather than a generic CRUD look. Alternatives considered: Svelte 5 with SvelteKit (prerelease major at the time), Vue 3, Solid (prerelease major), and utility-class styling.

## Decision

React 19 with TypeScript, built with Vite and served by the backend as a single-page application. React Aria Components provide accessible primitives; TanStack Query manages server state; Dexie keeps the offline outbox in IndexedDB; `react-i18next` provides English and Spanish catalogues with the language stored on the user's account; `vite-plugin-pwa` produces the service worker. Styling uses design tokens as CSS custom properties in one file, CSS Modules per component and a Stylelint rule that forbids raw colours outside the token file; the same token file is imported by the PDF report templates. Storybook documents every component with accessibility checks.

## Consequences

- Two toolchains (uv and pnpm) and Node on the workstation; the frontend is type-checked against the generated API client.
- Bundle size is a secondary concern on a LAN or VPN next to photographs; correctness of touch and keyboard interaction is primary.
- The camera path is dual: native file input always, `getUserMedia` guided capture only in secure contexts and outside iOS standalone mode.
- Report PDFs and the application share one visual language by construction.
