# Basecoat UI Design System

This document defines the visual language and technical implementation of the Basecoat UI system for **Git Back Up**.

## 1. Brand & Style
- **Aesthetic:** Modern-Corporate / Utility-First.
- **Vibe:** Mission-control dashboard, authoritative, precise.
- **Goal:** High density, high legibility, minimal eye strain.

## 2. Color Palette (Dark-Mode First)

| Name | Hex | Usage |
| :--- | :--- | :--- |
| `surface` | `#11131b` | Canvas / Deepest background |
| `surface-container` | `#1d1f27` | Standard panels and cards |
| `surface-bright` | `#373942` | High-contrast panels |
| `primary` | `#b4c5ff` | Interactive elements / Branding |
| `primary-container` | `#2563eb` | Primary buttons / Active states |
| `on-surface` | `#e1e2ed` | Main text color |
| `outline` | `#8d90a0` | Borders and secondary labels |
| `error` | `#ffb4ab` | Failure states / Alerts |
| `success` | `#81c784` | Healthy states / Confirmations |

## 3. Typography
- **Primary Typeface:** `Inter` (UI labels, body copy, navigation).
- **Technical Typeface:** `Space Grotesk` (IDs, hashes, logs, metrics).

### Scales
- `display-mono`: 32px / 700 / Space Grotesk
- `heading-sm`: 18px / 600 / Inter
- `body-md`: 14px / 400 / Inter
- `code-sm`: 13px / 400 / Space Grotesk
- `label-caps`: 11px / 700 / Inter (Uppercase, 0.05em tracking)

## 4. Layout & Spacing
- **Grid:** 4px baseline.
- **Standard Padding:** 24px (`lg`), 16px (`md`), 8px (`sm`).
- **Dividers:** 1px hairline (`outline-variant`) for clear region delineation.
- **Sidebar Width:** 256px (64 units).

## 5. Elevation & Depth
- **Level 0:** Canvas (`surface`)
- **Level 1:** Panels (`surface-container-low`)
- **Level 2:** High-contrast blocks (`surface-container`)
- **Level 3:** Interactive / Hover states (`surface-variant`)
- **Shadows:** Tight and dark: `0 2px 4px rgba(0,0,0,0.5)`.

## 6. Components

### Status Chips (Pills)
- 20% background opacity.
- Solid high-chroma text.
- 6px leading dot indicator.

### Logs / Terminals
- Background: `surface-container-lowest`.
- Font: `Space Grotesk`.
- Line numbering on the left.

### Form Inputs
- Background: `surface-container`.
- Border: `outline-variant`.
- Focus Ring: 2px `primary`.
- Corner Radius: 4px (`0.25rem`).
