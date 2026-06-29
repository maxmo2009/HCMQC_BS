"""Load fitted template meshes (VTKs) for overlay on the 3D segmentation.

Each patient folder may carry a ``vtks/`` subdir with fixed-topology surfaces
produced by the heart-mesh-fitting stage:

    <patient>/vtks/F_<region>_<phase>.vtk   (region in LVendo/LVepi/LVmyo/RV)

The .vtk files are legacy ASCII POLYDATA in **world (mm)** coordinates, while the
3D viewer draws the segmentation in **voxel-index** space. We parse the surfaces
(pure-Python, no vtk/meshio dependency) and map their vertices back to voxel
indices with the segmentation's own affine, so the mesh overlays the voxels
exactly once the viewer applies its usual ``(idx - shape/2) * spacing`` transform.
"""

import os

import nibabel as nib
import numpy as np

from config import BASE_PATH

# Surface regions, in draw order. Mirrors heart_mesh_fitting REGIONS.
MESH_REGIONS = ("LVendo", "LVepi", "LVmyo", "RV")


def _parse_vtk_polydata(path):
    """Parse a legacy ASCII VTK POLYDATA file.

    Returns (verts (N,3) float64, faces (M,3) int64) — triangulating any
    non-triangular polygon by a simple fan. Raises ValueError on malformed input.
    """
    with open(path) as fh:
        toks = fh.read().split()

    try:
        pi = toks.index("POINTS")
    except ValueError:
        raise ValueError("no POINTS section")
    n_pts = int(toks[pi + 1])
    # toks[pi + 2] is the dtype ("double"/"float"); coords start after it.
    base = pi + 3
    verts = np.array(toks[base:base + n_pts * 3], dtype=np.float64).reshape(n_pts, 3)

    try:
        gi = toks.index("POLYGONS")
    except ValueError:
        raise ValueError("no POLYGONS section")
    n_cells = int(toks[gi + 1])
    size = int(toks[gi + 2])
    conn = np.array(toks[gi + 3:gi + 3 + size], dtype=np.int64)

    if size == n_cells * 4:  # fast path: all triangles ("3 i j k")
        faces = conn.reshape(n_cells, 4)[:, 1:]
    else:  # mixed polygon sizes — walk the connectivity and fan-triangulate
        faces = []
        j = 0
        while j < conn.size:
            c = int(conn[j])
            idx = conn[j + 1:j + 1 + c]
            j += 1 + c
            for k in range(1, c - 1):
                faces.append((idx[0], idx[k], idx[k + 1]))
        faces = np.array(faces, dtype=np.int64)
    return verts, faces


def _corrected_affine(img):
    """Return an affine whose voxel scale matches the header zooms.

    Most NIfTI files in these datasets have a **degenerate sform** — voxel
    spacing was lost (z recorded as 1 mm, or all-zero for savioli) while the
    true geometry survives in the **qform** (z = 10 mm). `nib.load().affine`
    prefers the sform, so a mesh mapped through it lands ~10× too long in z.

    Detect the degeneracy (affine column norms ≠ header zooms) and fall back to
    qform — mirroring the `_affine_with_spacing` logic used when the meshes were
    fitted, so mesh and image share one coordinate system. Returns the original
    affine when it's already consistent (e.g. rulebase_fixed) or when no usable
    qform exists.
    """
    affine = img.affine
    zooms = np.asarray(img.header.get_zooms()[:3], dtype=float)
    col_norm = np.linalg.norm(np.asarray(affine)[:3, :3], axis=0)
    if np.allclose(col_norm, zooms, rtol=0.05):
        return affine  # sform already carries the real spacing
    try:
        q = np.asarray(img.get_qform())
    except Exception:
        return affine
    if q is None or not np.all(np.isfinite(q)):
        return affine
    q_norm = np.linalg.norm(q[:3, :3], axis=0)
    # Only trust qform if IT matches the zooms; otherwise keep the original.
    return q if np.allclose(q_norm, zooms, rtol=0.05) else affine


def _world_to_voxel(verts_world, affine):
    """Map (N,3) world-mm vertices to voxel-index coordinates via inv(affine)."""
    inv = np.linalg.inv(affine)
    homog = np.c_[verts_world, np.ones(len(verts_world))]
    return (homog @ inv.T)[:, :3]


def load_patient_meshes(patient_path, phase="ED"):
    """Return fitted-mesh geometry for a patient/phase, in voxel-index space.

    {
      "available": bool,
      "regions": { "<region>": {"vertices": [[x,y,z],...], "faces": [[i,j,k],...]}, ... }
    }

    ``available`` is False (and ``regions`` empty) when the patient has no
    ``vtks/`` folder — the common case — so the viewer simply shows no overlay.
    """
    base = BASE_PATH + patient_path
    vtk_dir = os.path.join(base, "vtks")
    seg_path = os.path.join(base, f"seg_lvsa_SR_{phase}.nii.gz")

    if not os.path.isdir(vtk_dir) or not os.path.exists(seg_path):
        return {"available": False, "regions": {}}

    # Use the corrected affine (qform when the sform is degenerate) so the mesh
    # maps into the same voxel grid the viewer renders the segmentation in.
    affine = _corrected_affine(nib.load(seg_path))

    regions = {}
    for region in MESH_REGIONS:
        vtk_path = os.path.join(vtk_dir, f"F_{region}_{phase}.vtk")
        if not os.path.exists(vtk_path):
            continue
        try:
            verts_world, faces = _parse_vtk_polydata(vtk_path)
        except (ValueError, IndexError) as exc:
            print(f"mesh_loader: skip {vtk_path}: {exc}")
            continue
        verts_vox = _world_to_voxel(verts_world, affine)
        regions[region] = {
            "vertices": np.round(verts_vox, 3).tolist(),
            "faces": faces.tolist(),
        }

    return {"available": bool(regions), "regions": regions}
