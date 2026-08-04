# Simple Collider

Simple Collider is a Blender addon for creating physics colliders for games and real-time applications.

## Features

* Collider shapes: Box, Sphere, Cylinder, Capsule, Convex Hull, K-DOP (10/18/26), Minimum/Aligned Bounding Box,
  Re-meshed (voxel remesh), and full-detail Mesh.
* Auto Convex decomposition using V-HACD, plus an alternative CoACD backend for higher-precision (but slower)
  results.
* Validation Checks (BETA): scan the scene or selection for missing colliders, non-manifold geometry, flipped
  normals, oversized triangle counts, mismatched bounding boxes, naming/parenting conventions, missing physics
  materials, and more - configurable per-check in preferences.
* Collider Groups for organizing and toggling visibility of related colliders.
* Physics Materials for tagging materials used by colliders.
* Shape conversion, renaming, and rigid body setup utilities.

See [CHANGELOG.md](CHANGELOG.md) for what's new in each release.

## Stores

Support me by purchasing the addon from following stores:

* [Gumroad](https://weisl.gumroad.com/l/simple_collider "Gumroad")
* [Superhive](https://superhivemarket.com/products/simple-collider "Superhive")

You are permitted to get a copy from this GitHub page and everything specified in the attached license (GPL 3.0).
Creating addons is a lot of effort and work. The licensing and contribution of my future addons will also depend on the
fairness of all of you.

Alternatively, you can also make a donation via PayPal. Full support will only be available for customers of the stores
though!

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate/?hosted_button_id=Q6PL92LJX7836)

## Contribution

The best and easiest way to contribute is to share your experiences and use cases with me. Seeing how you work, helps me
to understand what you need.

Pull requests are also very welcome. Feel free to contact me before working on your changes and making a pull request.
Let's see if the proposed changes fit the overall design and purpose of this addon. I will be strict in keeping a
consistent user experience and vision for this addon.

## Development & Testing

`tests/` contains `unittest`-based integration tests that run inside headless Blender against real `bpy`/`bmesh`
objects and operators. Run the whole suite with one command:

```
python tests/run_tests.py --blender /path/to/blender
```

(`--blender` defaults to `blender` on `PATH`.) Each test file can still be run individually, as documented in its own
docstring, e.g. `blender --background --python tests/test_bounding_sphere.py`.

CI (`.github/workflows/tests.yml`) runs this same suite on every push/PR across a matrix of Blender 4.2, 4.3, 4.4,
4.5, 5.0 and 5.1 to catch version-specific API breakage.