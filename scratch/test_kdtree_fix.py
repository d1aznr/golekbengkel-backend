import numpy as np
from scipy.spatial import KDTree

# Setup
node_positions = {
    1: (-6.8, 111.8),
    2: (-7.0, 111.9)
}
nodes = list(node_positions.keys())
positions = np.array([node_positions[n] for n in nodes])
kdtree = KDTree(positions)

# Test 2D input (current code)
point_2d = np.array([[-6.867, 111.849]])
_, idx_2d = kdtree.query(point_2d, k=1)
print(f"2D Input - idx: {idx_2d}, type: {type(idx_2d)}, shape: {getattr(idx_2d, 'shape', 'N/A')}")
try:
    print(f"int(idx_2d): {int(idx_2d)}")
except Exception as e:
    print(f"int(idx_2d) failed: {e}")

# Test 1D input (proposed fix)
point_1d = np.array([-6.867, 111.849])
_, idx_1d = kdtree.query(point_1d, k=1)
print(f"1D Input - idx: {idx_1d}, type: {type(idx_1d)}, shape: {getattr(idx_1d, 'shape', 'N/A')}")
try:
    print(f"int(idx_1d): {int(idx_1d)}")
except Exception as e:
    print(f"int(idx_1d) failed: {e}")
