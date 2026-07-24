# Changelog

All notable changes to Simple Collider are documented here. Dates are set when
a version is actually tagged/released.

## [1.2.0] - Unreleased

### Added

- **Validation Checks (BETA)** — a new "Validate Colliders" report (N-panel)
  that scans the scene or current selection for common collider problems:
  missing colliders, non-manifold geometry, flipped normals, oversized
  triangle counts, colliders that are too small, mismatched bounding boxes,
  too many colliders per render mesh, naming-convention mismatches, missing
  parenting, missing physics materials, and (optional, off by default)
  heuristic checks for shapes that don't match their claimed type (box,
  convex, etc.) or that could use a simpler primitive. Every check can be
  toggled and tuned individually in preferences.
- **Auto Convex (BETA) using CoACD** — an alternative convex decomposition
  backend alongside the existing V-HACD integration, with its own set of
  preferences (resolution, MCTS search parameters, preprocessing mode, etc.).

### Changed

- Capsule collider generation is no longer marked BETA.
- Improved handling of multi-scene setups and ignored linked libraries.
- Various responsiveness improvements to collider creation/conversion
  (fewer redundant depsgraph evaluations while dragging modal parameters).
- Updated 3D viewport navigation during collider creation.
- Changed default keybindings for several operators.
- Added a "reload add-on" button to preferences for faster iteration.
- A warning is now shown when creating a collider for an object with no
  rigid body set.
- Convert operators are now disabled (rather than failing) when the
  current selection isn't a valid target.

### Fixed

- Fixed a false negative in parent-inverse shear detection that could let
  a sheared parent transform silently distort a collider.
- Fixed collider instances not being initialized properly in some scenes.
- Fixed a crash during collider creation in certain scenes.
- Fixed viewport drawing overlays being removed when an operator failed.

### Removed

- Removed the debug-only preferences flag (`Prefs.debug`) and the code
  paths behind it.
- **Simple Mesh** (the voxel-grid collider operator introduced during 1.2.0
  development) has been pulled from this release — it overlapped too much
  with the existing "Add Re-meshed" operator without adding a distinct
  use case. The underlying geometry code is kept on a separate branch for
  a future, properly-scoped redesign.

### Known limitations

- Validation Checks and Auto Convex (CoACD) both ship as BETA: expect rough
  edges, and please report issues so they can be addressed before their
  BETA label is removed.
