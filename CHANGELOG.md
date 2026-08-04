# Changelog

All notable changes to Simple Collider are documented here. Dates are set when
a version is actually tagged/released.

Each version below mirrors the structure used on the
[documentation site's release notes page](https://weisl.github.io/simple_collider/collider_release_notes/):
a short summary of the release, followed by "Features & Improvements" and
"Bug Fixes" lists whose entries link back to their GitHub issue. New releases
are added as a new section above the previous one — existing entries are
never overwritten, so this file (like the docs page) accumulates the full
release history over time.

## Simple Collider v1.2.0 (Unreleased)

This release adds scene-wide collider validation and an alternative
CoACD-based Auto Convex backend, alongside a round of responsiveness and
stability fixes for collider creation and conversion.

### Features & Improvements

- [#548](https://github.com/Weisl/simple_collider/issues/548): **Validation
  Checks (BETA)** — a new "Validate Colliders" report (N-panel) that scans
  the scene or current selection for common collider problems: missing
  colliders, non-manifold geometry, flipped normals, oversized triangle
  counts, colliders that are too small, mismatched bounding boxes, too many
  colliders per render mesh, naming-convention mismatches, missing
  parenting, missing physics materials, and (optional, off by default)
  heuristic checks for shapes that don't match their claimed type (box,
  convex, etc.) or that could use a simpler primitive. Every check can be
  toggled and tuned individually in preferences.
- [#583](https://github.com/Weisl/simple_collider/issues/583): **Auto Convex
  (High Precision) using CoACD** — an alternative convex decomposition
  backend alongside the existing V-HACD integration, producing tighter
  hulls at the cost of being significantly slower, with its own set of
  preferences (resolution, MCTS search parameters, preprocessing mode,
  etc.).
- [#660](https://github.com/Weisl/simple_collider/issues/660): Auto Convex
  (both V-HACD and CoACD) now runs asynchronously with a live progress
  overlay (phase, percentage, elapsed time) instead of freezing Blender
  for the duration of the run — Escape cancels a run in progress.
- [#642](https://github.com/Weisl/simple_collider/issues/642): Capsule
  collider generation is no longer marked BETA.
- [#552](https://github.com/Weisl/simple_collider/issues/552): Improved
  handling of multi-scene setups and ignored linked libraries.
- [#555](https://github.com/Weisl/simple_collider/issues/555): New **Post
  Processing** preferences tab with "Auto Apply on Creation" options —
  automatically limit newly created colliders to a target triangle count
  and/or move their origin to match their parent's, right after creation.
- [#631](https://github.com/Weisl/simple_collider/issues/631),
  [#638](https://github.com/Weisl/simple_collider/issues/638),
  [#641](https://github.com/Weisl/simple_collider/issues/641): Various
  responsiveness improvements to collider creation/conversion (fewer
  redundant depsgraph evaluations and a cached modifier-stack bake while
  dragging modal parameters).
- [#640](https://github.com/Weisl/simple_collider/issues/640): The modal HUD
  now allows typing numeric values directly instead of only mouse-dragging.
- [#635](https://github.com/Weisl/simple_collider/issues/635): Updated 3D
  viewport navigation and HUD colors/backdrop during collider creation.
- [#634](https://github.com/Weisl/simple_collider/issues/634): Changed
  default keybindings for several operators.
- [#627](https://github.com/Weisl/simple_collider/issues/627): Added a
  "reload add-on" button to preferences for easier development.
- [#628](https://github.com/Weisl/simple_collider/issues/628): A warning is
  now shown when creating a collider for an object with no rigid body set.
- [#636](https://github.com/Weisl/simple_collider/issues/636),
  [#637](https://github.com/Weisl/simple_collider/issues/637): Convert
  operators are now disabled (rather than failing) when the current
  selection isn't a valid target.
- [#643](https://github.com/Weisl/simple_collider/issues/643): Removed the
  debug-only preferences flag (`Prefs.debug`) and the dead
  `debug_parenting_off` flag, along with the code paths behind them.
- The update checker now respects Blender's "Allow Online Access"
  preference before making its network request, and the manifest now
  declares this network permission.


### Bug Fixes

- [#558](https://github.com/Weisl/simple_collider/issues/558),
  [#639](https://github.com/Weisl/simple_collider/issues/639): Fixed a false
  negative in parent-inverse shear detection that could let a sheared
  parent transform silently distort a collider.
- [#630](https://github.com/Weisl/simple_collider/issues/630): Fixed
  collider instances not being initialized properly in some scenes.
- [#629](https://github.com/Weisl/simple_collider/issues/629): Fixed a crash
  when interacting with sphere segment counts below 2.
- [#625](https://github.com/Weisl/simple_collider/issues/625): Fixed
  viewport drawing overlays being removed when an operator failed.
- [#644](https://github.com/Weisl/simple_collider/issues/644),
  [#645](https://github.com/Weisl/simple_collider/issues/645),
  [#646](https://github.com/Weisl/simple_collider/issues/646),
  [#647](https://github.com/Weisl/simple_collider/issues/647),
  [#648](https://github.com/Weisl/simple_collider/issues/648): Hardened
  Validation Checks — fixed a crash on regex metacharacters in the naming
  check, render-object types (curve/surface/font/metaball) being skipped by
  several checks, one object's failure aborting the entire scan, results
  persisting across file loads instead of being scoped per file, and added
  progress feedback for large-scene scans.
- [#660](https://github.com/Weisl/simple_collider/issues/660): Fixed a
  crash and silent transform/parenting loss on hulls when an Auto Convex
  job finished while the mouse wasn't over the 3D viewport.

### Known limitations

- Validation Checks ships as BETA: expect rough edges, and please report
  issues so they can be addressed before its BETA label is removed.
