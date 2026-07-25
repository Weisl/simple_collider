# Manual QA Checklist — Simple Collider

Automated tests (`tests/`) only cover pure geometry functions and a few
non-modal operators run headless. Everything interactive — modal hotkeys,
mouse-drag, the HUD, viewport behavior, preference toggles, panels — is
**not** exercised by CI and needs a human. Use this before every release.

- **Short list**: ~15–20 min smoke test, run before any dev build / PR merge.
- **Long list**: full pass before a tagged release. Organized by addon area.

Each item is phrased as a question with the expected result after "→".
Check the box once verified; note the actual Blender version tested.

Blender version tested: ______  OS: ______  Date: ______

---

## SHORT LIST (Smoke Test)

- [ ] Add Box / Sphere / Cylinder / Capsule / Convex Hull / K-DOP / Mesh /
  Re-meshed collider on a simple selected mesh → each creates a collider,
  named per convention, placed in the "Colliders" collection.
- [ ] During creation, drag to resize (mouse move) and press `LEFTMOUSE` to
  confirm → collider keeps the dragged size; no leftover temp objects.
- [ ] Start a shape operator, press `ESC` → operator cancels, no collider or
  temp mesh/collection left behind.
- [ ] Run Auto Convex (V-HACD) on a simple mesh with default settings →
  produces one or more convex hull colliders without hanging Blender.
- [ ] Run Auto Convex (CoACD, BETA) once with default settings → completes
  and produces hulls (acceptable to be rougher — it's BETA).
- [ ] Convert to Collider on a plain mesh object → object becomes a collider
  in place; Convert to Mesh on a collider → reverses it back to a normal
  render mesh.
- [ ] Run "Validate Colliders (BETA)" on a scene with at least one known-bad
  collider (e.g. huge triangle count) → reports the issue with correct
  severity; "Copy Report to Clipboard" produces readable text.
- [ ] Toggle a Collider Group's visibility eye icon in the N-panel → matching
  colliders hide/show in the viewport.
- [ ] Open Preferences → Simple Collider, switch through all tabs (Settings,
  Post Process, Naming, Keymap, UI, VHACD, Validation, Support) → each tab
  draws without errors in the console.
- [ ] Apply a naming preset (e.g. UE-default) → naming tokens/material prefs
  update; generate a new collider afterward and confirm its name matches
  the new convention.
- [ ] Open the Collider Pie Menu (default `Ctrl+Shift+C`) in the viewport →
  menu appears with shape/creation options and works.
- [ ] Save the .blend, close, and reopen it → collider groups, colors, and
  pinned default preset are restored correctly.

---

## LONG LIST (Full Release Pass)

### 1. Shared modal operator behavior (applies to every shape operator)

- [ ] `G`/`L` toggles Global/Local space (box, capsule, cylinder, min-bbox)
  → HUD label updates and generated bounds change accordingly.
- [ ] `M` cycles Creation Mode (Individual ↔ Selection) → collider count
  changes as expected (one per object vs. one for the whole selection).
- [ ] `T` cycles Collider Group (only when Collider Groups are enabled in
  prefs) → HUD shows the new group name; final collider is tagged/colored
  for that group.
- [ ] `V` cycles shading/preview color mode → viewport color changes live
  during the modal.
- [ ] `Q` cycles "Shape Overwrite" after a collider already exists (only
  where `use_shape_change` applies) → re-tags shape + renames without
  regenerating geometry.
- [ ] `X`/`Y`/`Z` changes axis on cylinder/capsule → orientation updates live.
- [ ] `C` toggles X-Ray → viewport X-ray toggles for the temp object.
- [ ] `I` toggles "Use Loose Islands" → splitting a multi-island selection
  produces one collider per island instead of one combined collider.
- [ ] `J` toggles "Join Primitives" → merges all generated colliders into a
  single mesh object and forces shape tag to `mesh_shape` while active.
- [ ] `P` toggles "Use Modifier Stack" → bounds are computed from the
  modifier-evaluated mesh vs. the base mesh (test on an object with a
  Subdivision or Mirror modifier).
- [ ] `O` toggles "Keep Original Materials" (mesh/remesh/convert-to-collider)
  → collider keeps source materials vs. gets the physics material.
- [ ] `N` toggles "Keep Original Name" (Convert to Collider, Object Mode
  only) → base object's original name is preserved vs. renamed to convention.
- [ ] `A` + mouse move drags opacity; `CTRL` snaps, `SHIFT` fine-tunes →
  value changes match modifier key behavior.
- [ ] `S` drags Shrink/Inflate (Displace strength) → mesh visibly
  shrinks/grows; leaving it at exactly 0 and confirming removes the
  Displace modifier (when "Keep Modifier Defaults" pref is on, its default).
- [ ] `D` drags Decimate ratio → is debounced (no viewport stutter/freeze
  while dragging on a dense mesh, regression for #641); leaving at default
  and confirming removes the Decimate modifier.
- [ ] `R` drags sphere/capsule segment count or Remesh voxel size (shape
  dependent) → dragging to the minimum doesn't crash (sphere segments floor
  at 2); Remesh voxel-size drag is debounced on a dense source mesh (#641).
- [ ] `H`/`W` drag height/width multiplier on capsule (range 0–10) → capsule
  proportions update live, clamps at the range ends.
- [ ] **Numeric text entry** (#640): while a drag field (S/D/A/E/H/W/R) is
  active, type digits → switches to typed-value mode; `RET` confirms,
  `ESC`/empty-`BACKSPACE` cancels back to drag mode; typing non-numeric text
  is ignored with a WARNING; typing `-` toggles sign; a second `.` is
  ignored (no duplicate decimal points).
- [ ] Right-click while a numeric field is being typed → hard-cancels the
  entire operator (not just the field).
- [ ] Orbit (MMB) / zoom (wheel) mid-drag → HUD dims during navigation and
  un-dims roughly 0.2s after navigation stops, even if the mouse goes idle
  right after; an active S/D/A drag doesn't fight the orbit.
- [ ] Hold `ALT` during a mouse-drag field → input is ignored (HUD shows
  "IGNORE INPUT (ALT)"); releasing `ALT` doesn't cause a value jump.
- [ ] HUD backdrop toggle (`use_modal_box` pref) → HUD box shows/hides;
  re-color each of the 7 modal color roles (default/title/highlight/error/
  navigation/modal/bool/enum) and confirm each is visually distinct.
- [ ] Test the HUD at a very small and very large `modal_font_size`, and at
  non-1.0 Blender `ui_scale` (HiDPI) → text stays legible, not clipped
  (regression for #623).
- [ ] Cancel (`RIGHTMOUSE`/`ESC`) after toggling several hotkeys (M/T/V/I/J/
  P/O/N) → everything cleans up fully, no dangling temp collections/objects,
  no leftover modal/draw handler (try triggering another modal afterward).

### 2. Post-processing & confirm-time cleanup

- [ ] Confirm a collider whose parent has non-uniform scale + rotation
  (shear) → collider is NOT distorted; a WARNING is reported instead of
  silently baking a bad parent-inverse matrix.
- [ ] Confirm a collider whose parent has a "normal" (no-shear) transform →
  parent-inverse matrix bake happens silently, no warning.
- [ ] Turn on "Auto Apply Triangle Limit" and "Auto Apply Origin to Parent"
  (both off by default) → newly created colliders get their modifiers
  auto-applied and origin auto-set; a collider that can't reach the
  triangle limit even at max decimation reports a WARNING per object.
- [ ] Origin recentering to center of mass happens on confirm unless
  "Join Primitives" was used (joined result keeps its own origin logic).
- [ ] Toggle "Hide After Creation" and "Wireframe Mode" (Off/Preview/Always)
  in prefs → newly created colliders match those settings exactly.
- [ ] Toggle "Hide Render on Creation" (default ON) → new colliders are
  render-hidden by default; turning it off makes them render-visible.
- [ ] Create a collider from an object with an un-realized Geometry Nodes
  "Instance on Points" (no "Realize Instances") → collider still captures
  every instance's geometry (`merge_object_instances` walks depsgraph
  instances manually).
- [ ] Two scenes in the same file, each generating colliders → each scene
  gets its own "Colliders" collection, suffixed `_01`/`_02` (not Blender's
  own `.001` convention) rather than colliding.

### 3. Edge cases / degenerate input

- [ ] Select 0 vertices (Edit Mode) or select nothing (Object Mode) and run
  a shape operator → HUD shows red "Selection Invalid"; confirming reports
  "No Colliders generated" WARNING, nothing is created.
- [ ] Minimum Bounding Box with only 1 or 2 selected vertices → object is
  skipped (needs ≥3 verts), no crash.
- [ ] Sphere collider on a single vertex, two vertices, and a perfectly flat
  (coplanar) selection → each produces a valid (if degenerate) sphere, no
  crash (Welzl degenerate-case handling).
- [ ] Drag sphere/capsule segment count down to its floor → clamps at 2,
  no divide-by-zero crash.
- [ ] Generate a 10-DOP on a visibly asymmetric/lopsided mesh → all 10 faces
  are present and not truncated on any axis pair (regression check — two
  normals were previously missing).
- [ ] Feed a very large or oddly-shaped selection into a shape operator →
  doesn't throw an unhandled exception (should cleanly cancel + report an
  ERROR if something goes wrong internally, not leave a broken modal).

### 4. Auto Convex — V-HACD

- [ ] Adjust `maxHullAmount`, `maxHullVertCount`, `voxelResolution`, and the
  shrinkwrap toggle in the popup → decomposition result visibly changes
  (more/fewer hulls, tighter/looser fit).
- [ ] Adjust advanced VHACD prefs (volume error %, min edge length, max
  recursion depth, fill mode, optimal split plane) → operator still runs
  and produces different results from the fill-mode change.
- [ ] Point `executable_path` at a non-existent file → clear ERROR reported,
  operator cancels cleanly (no hang, no partial output).
- [ ] On Linux/Mac, `chmod -x` the bundled executable → Preferences UI shows
  "Missing Permission" ERROR with a "How to Fix" link (don't just check the
  operator — check the *preferences panel* surfaces this too).
- [ ] Point the temp `data_path` at a non-existent or read-only folder →
  falls back to the system temp dir silently (no user-facing error, only
  console) — confirm decomposition still completes.
- [ ] Run V-HACD on a very large/dense mesh → note whether Blender's UI
  freezes for the duration (no timeout exists on the subprocess wait) and
  whether that's acceptable for release, or worth a follow-up.
- [ ] Run V-HACD on a mesh that yields zero hulls (e.g. a single triangle)
  → "No meshes to process!" WARNING, clean cancel.
- [ ] On an unsupported platform (e.g. Intel Mac) → the Auto Convex button
  is hidden entirely and prefs show an unsupported-platform message instead
  of a broken button.

### 5. Auto Convex — CoACD (BETA)

- [ ] Confirm the operator/label/prefs all clearly read "BETA" so testers
  don't hold it to the same bar as V-HACD.
- [ ] Enable `coacd_decimate` with a low `coacd_maxHullVertCount` → each
  hull actually gets vertex-limited (check per-hull vert counts before/
  after); a hull whose decimation fails reports "CoACD hull decimation
  failed for {name}, keeping original hull" WARNING rather than losing it.
- [ ] Run CoACD on a multi-object selection where one object is degenerate
  (e.g. flat plane) → that object reports "CoACD failed to generate
  colliders for {name}" WARNING but the rest of the batch still completes.
- [ ] Same executable-missing / permission / unsupported-platform checks as
  V-HACD (§4) repeated for CoACD's own executable/path prefs.
- [ ] Adjust preprocess mode (auto/on/off), resolution, MCTS iterations/
  depth/nodes, no-merge, PCA toggles → operator still completes and results
  visibly differ between "off" and "on" preprocessing.

### 6. Convert operators

- [ ] Convert to Collider, then cancel mid-modal (`ESC`) after toggling
  `N`/`O`/`M` a few times → base object's name, collection, and visibility
  are perfectly restored, as if nothing happened.
- [ ] Convert to Collider on a Curve, Surface, Font (Text), and Metaball
  object (not just Mesh) → each converts correctly.
- [ ] Convert to Collider on a linked-duplicate (multi-user mesh data)
  object, alongside its sibling instances → only the converted object
  changes; sibling instances keep their original mesh data untouched.
- [ ] Convert to Mesh on multiple selected colliders at once → each gets
  its own unique generated name, no name collisions.
- [ ] Convert to Mesh on a collider that's the *only* member of its
  collection → object re-links to the scene root collection instead of
  being left orphaned.
- [ ] Convert to Empty on a box collider and a sphere collider → produces a
  CUBE/SPHERE empty respectively with correct half-extent/radius scale.
- [ ] Convert to Empty with a mixed selection including a convex/mesh
  collider (unsupported shapes) → box/sphere ones convert, others are
  silently skipped, and the reported count matches only the converted ones.
- [ ] Convert to Empty on a degenerate (near-zero-size) collider → empty
  gets a floor scale (1e-6), not a literal zero scale.
- [ ] "Assign Collider Shape" (shape icon row) on an existing collider →
  re-tags shape + renames, no geometry regenerated.
- [ ] "Convert From Name" on an object renamed by hand to match a naming
  preset's convention (never run through the addon) → `isCollider`/shape/
  group get correctly back-filled; run it again on a name matching no
  pattern → "No collider has been detected" WARNING, nothing changes.
- [ ] "Regenerate Name" run twice in a row on the same selection → second
  run is a no-op (cancelled, not finished) and doesn't add a spurious undo
  step (check the undo history).

### 7. Rigid Body naming

- [ ] Run "Set Rigid Body" on selected objects with the extension string
  configured → name gets the prefix/suffix appended per
  `rigid_body_naming_position`.
- [ ] Run it again on the same objects → skips already-tagged names,
  reports WARNING + cancelled (nothing to rename).
- [ ] Clear the `rigid_body_extension` preference to empty and run the
  operator → WARNING "Rigid Body extension not defined!"
- [ ] Rename a render mesh via Set Rigid Body first, *then* generate a
  collider on it → generated collider's name does not include the rigid-
  body tag twice.

### 8. Collider Groups

- [ ] Assign a collider to each of the 3 user groups via "Assign User
  Group" → viewport color and name both update to match the new group.
- [ ] Toggle a group's hide icon → only objects in the *current view layer*
  hide/show (an object linked to another scene/view layer is unaffected).
- [ ] Toggle a group's select icon → selection applies scene-wide across
  `bpy.data.objects`, independent of view layer — confirm this differs
  from the hide behavior above (hide = view-layer-scoped, select = not).
- [ ] Rename a group's display name and change its color in Preferences →
  N-panel section and existing colliders' viewport colors update to match.
- [ ] Start a fresh Blender session with no prior .blend (factory defaults)
  → default group names/colors/tokens populate correctly.
- [ ] Open an old .blend saved before Collider Groups existed → groups get
  sane default values without erroring.

### 9. Preferences (full pass)

- [ ] Toggle "Use Collider Collection" off → new colliders are not placed
  in a dedicated collection.
- [ ] Change the naming: prefix vs. suffix position, custom separator,
  base name, digit count, custom pre/suffix strings, and each shape's
  naming token → generate one collider per change and confirm the name
  matches exactly.
- [ ] Set a shape's naming token to empty (mesh_shape is empty by default)
  → generated name omits the shape token cleanly (no dangling separator).
- [ ] Toggle "Use Physics Material" and its sub-options (skip material,
  naming position, custom pre/suffix, random color, default material name/
  filter) → new colliders get/don't get a physics material as configured.
- [ ] Apply each of the 4 built-in naming presets (UE, Unity, Northlight,
  Godot) in turn → all ~25 snapshot values update together; generate a
  collider after each to confirm the full convention applies correctly.
- [ ] Pin a preset as default, restart Blender / reopen the file → pinned
  preset auto-loads on file open.
- [ ] Save a custom user preset, then load an **old-format** preset file
  (pre-dating newer properties, if one is available) → the upgrade
  operator fills in missing keys with sane defaults, no crash.
- [ ] Assign all 3 configurable keymap hotkeys (Pie Menu, Visibility Menu,
  Material Menu) to custom key combos, including one that collides with a
  built-in Blender shortcut → confirm what happens (documented tradeoff,
  not necessarily a bug, but should be understood before release).
- [ ] Remove a hotkey via its reset/remove button → confirm it's fully gone
  (check it doesn't still fire).
- [ ] Enable the two menus that are inactive by default (Visibility Menu,
  Material Menu) → confirm they now fire on their configured hotkey.
- [ ] Change `collider_category` (N-panel tab name) → panel moves to the
  new tab name in the 3D viewport N-panel.
- [ ] With no internet connection, open the addon (triggers the background
  update-check thread) → no error/crash, simply no "update available"
  banner (silent failure by design).

### 10. Validation (BETA)

For each check below: construct a scene that should trigger it, run
"Validate Colliders (BETA)", and confirm the message, severity (WARNING
vs. ERROR), and which object it's attached to are all correct.

- [ ] Missing Collider — a render mesh with no child collider (only
  triggers if "Use Parent To" pref is on).
- [ ] Triangle Count — collider's post-modifier tri count over the
  configured max (default 255).
- [ ] Min Dimension — collider's raw (pre-modifier) bbox is smaller than
  the configured minimum on at least one axis (test with a Mirror/Solidify
  modifier on top of a genuinely flat base mesh — the check should still
  fire since it looks at the *raw* mesh).
- [ ] BBox Mismatch — the combined AABB of *all* of a mesh's colliders vs.
  the render mesh's own AABB differs beyond tolerance (test with several
  colliders that together roughly cover the mesh — should NOT fire per
  individual collider).
- [ ] Too Many Colliders — a render mesh with more child colliders than the
  configured max (default 8).
- [ ] Naming Convention — a collider renamed to not contain its shape's
  token.
- [ ] Non-Manifold (ERROR) — a collider mesh with a hole/open edge.
- [ ] Flipped Normals (ERROR) — a fully manifold collider with inverted
  normals (negative signed volume); confirm an open/non-manifold mesh does
  NOT also trigger this one (should be skipped, not double-reported).
- [ ] Missing Physics Material — a collider with no `isPhysicsMaterial`
  material assigned.
- [ ] Parent Hierarchy — a parentless collider, a collider parented to
  another collider, and a collider parented to an invalid object type —
  each should be flagged (unless "Use Parent To" is off).
- [ ] Convexity/Box/Mesh-could-use-primitive/Collision-Shape-Mismatch
  checks (all off by default) — enable each in turn and confirm they only
  fire on the intended shape mismatch, not false-positive on a normal
  well-formed collider.
- [ ] Scope toggle (Whole Scene vs. Selected Objects) → switching live
  re-scans and the result count changes appropriately.
- [ ] Filter by Errors/Warnings toggle buttons, and free-text search across
  object name + message → filtering doesn't break the per-object header
  grouping (test with several different flagged objects interleaved).
- [ ] Click the "select and frame" arrow on a result row from a context
  with no 3D viewport open (e.g. Preferences window) → doesn't error, falls
  back to finding a VIEW_3D area in any open window.
- [ ] "Copy Report to Clipboard" with results present, and with zero
  results ("No validation issues to copy" INFO) → both behave correctly.
- [ ] Manually corrupt a custom property (e.g. set `collider_shape` to
  garbage via the Python console) and re-run validation → the scan
  completes for the rest of the scene, with that one object's failure
  reported as its own error rather than crashing the whole scan.
- [ ] Run validation on a scene with many objects → progress bar shows and
  the UI doesn't appear frozen/unresponsive.

### 11. UI / Panels

- [ ] N-panel "Simple Collider" tab shows all sections (naming presets, Add
  Shape buttons, creation menu, Collider Groups visibility grid, collapsed
  "Tool Defaults", Physics Materials list) and none throw console errors.
- [ ] Open the Pie Menu and trigger every direction (Box/Cylinder/Convex
  Hull/Mesh/Sphere) plus the South box's full creation menu and visibility
  toggles.
- [ ] Open both popup panels (Visibility Menu, Material Menu) via their
  hotkeys once enabled.
- [ ] Resize the N-panel to a very narrow width → long text (e.g. platform-
  support strings) wraps instead of overflowing off-panel.
- [ ] Confirm there is genuinely no "Object menu" entry for these operators
  (everything lives in N-panel/pie menu) — if that's expected, fine; flag
  if the user expects one.
- [ ] Cycle `V` (object/material/preview color) and the dedicated "View by
  Object Color" / "View by Material" buttons → viewport shading switches to
  Solid and colors update accordingly.
- [ ] Toggle the wireframe overlay icon button → `show_wire` toggles on
  selected colliders live (not just at creation time).

### 12. Presets vs. Tool Defaults (naming confusion check)

- [ ] Confirm your understanding matches the addon: "Presets" = naming/
  material convention snapshots (UE/Unity/Northlight/Godot + user-saved);
  "Tool Defaults" (N-panel, collapsed section) = plain scene-level defaults
  (Global/Local, modifier stack, join primitives, cylinder axis/segments,
  sphere segments, voxel size) applied at operator invoke time, not a
  save/load preset list. Verify neither is mislabeled in the UI.

### 13. Engine interop — Unity / Unreal / Godot naming conventions

The addon has no export operator of its own — it only sets naming/material
conventions in Blender (`presets/presets_data.py`). Every item below needs an
actual FBX/glTF export and an import into the real target engine editor, since
nothing here is exercised by CI.

- [ ] Apply "UE-default" preset, generate Box/Sphere/Capsule/Convex Hull
  colliders on a render mesh (e.g. "Wall") → names are prefixed `UBX_`/
  `USP_`/`UCP_`/`UCX_` respectively; export as FBX and import into Unreal
  Engine → each is auto-detected as simple collision of the matching
  primitive shape, not imported as a separate visible static mesh.
- [ ] Generate multiple convex-hull islands on one mesh with UE-default
  (`UCX_Wall_00`, `UCX_Wall_01`, …) → on FBX import into Unreal, all numbered
  hulls are picked up as one compound collision, not just the first.
- [ ] Parent a UBX/USP/UCP collider to an object with shear (non-uniform
  scale + rotation) → confirm the shear WARNING fires and the parent-inverse
  is *not* silently baked; export to Unreal anyway and confirm the collider
  imports visibly misplaced/misshapen (documents the known limitation rather
  than a silent corruption).
- [ ] Parent a UBX/USP/UCP collider to a normal (non-sheared) parent, run
  "Fix Parent Inverse Matrix", then export/import into Unreal → the
  primitive keeps its canonical axis-aligned local shape with position/
  rotation carried entirely by the transform (regression check for the
  inverse-matrix fix in `utility_operators.py`, "Fix inverse matrix Auto").
- [ ] Apply "Unity-default" preset, generate each shape → names are suffixed
  descriptively (`_Box`/`_Sphere`/`_Capsule`/`_Convex`/`_Mesh`) and
  `replace_name` forces the base to "Collider"; after FBX import into Unity,
  confirm objects appear as plain named child GameObjects with mesh data and
  do **not** automatically become Collider components — Unity has no
  built-in naming-token auto-import like UE/Godot, so this is expected
  manual/external setup, not a bug.
- [ ] With Unity-default's physics material enabled (`COL_DEFAULT`/`COL`
  filter) → the assigned Blender material's slot/name survives FBX import
  as a material on the collider mesh (Unity does not read it as a
  PhysicMaterial asset — that mapping is manual).
- [ ] Apply "Godot-default" preset (separator `-`, collider groups off),
  generate each shape → names end in `-convcolonly` (box/sphere/capsule/
  convex) or `-colonly` (mesh), e.g. `geo-convcolonly`; export as glTF/.blend
  and import into Godot → Godot auto-generates a matching collision shape
  (convex vs. trimesh) per its `-colonly`/`-convcolonly` convention rather
  than importing the collider as a separate visible mesh.
- [ ] Godot-default's rigid body suffix (`rigid`, separator `-`) → run "Set
  Rigid Body" → confirm `-` (not `_`) is used and it composes cleanly
  alongside a `-convcolonly` collider suffix without a doubled separator.
- [ ] For all three engines/presets, generate a second collider with a name
  that collides so `unique_name()` appends its digit suffix (e.g.
  `UCX_Wall_01`, `geo-convcolonly.001`) → confirm the digit/uniquifier
  placement doesn't break the target engine's naming-pattern recognition
  (Unreal expects trailing digits right after the shape token; Godot expects
  its suffix at the very end of the name, so a Blender `.001` uniquifier
  landing after it is worth confirming either way).
- [ ] Confirm this addon has no bundled FBX/glTF export operator (by design —
  "Simple Export" mentioned in Preferences is a separate paid add-on) → test
  with Blender's standard exporters and each engine's typical import
  settings, rather than expecting the addon to configure exporter options.

### 14. Known-incomplete / release-blocking questions to resolve before ship

- [ ] The voxel-grid "Simplified Mesh" collider (diagonal-fill remesh
  engine in `bmesh_operations/voxel_generation.py`) has full geometry code,
  unit tests, and HUD/naming plumbing (`use_diagonal_fill`, `voxel_shape`
  token) — but **no operator ever calls it and it isn't registered or drawn
  in any menu.** Confirm with yourself/changelog whether this is
  intentionally held back for a later release. If so, make sure nothing in
  the UI or docs implies it's available now.
- [ ] Re-verify the specific historical bugs referenced in code comments
  are actually fixed in this build: #249 (edit-mode vertex reads with
  modifiers), #328 (`AttributeError` when `context.object` is None), #623
  (HUD font size vs. HiDPI `ui_scale`), #631 (modifier-bake caching during
  drag), #640 (numeric entry vs. hotkey conflicts), #641 (decimate/remesh
  debounce).
- [ ] Watch the status bar / Info log during the whole pass, not just for
  popups — several safety fallbacks (shear-skip on parent-inverse bake,
  unreachable triangle limit, CoACD per-hull failure) only ever report as
  a small WARNING in the status bar, easy to miss.
