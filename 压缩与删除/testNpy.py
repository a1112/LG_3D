import numpy as np

npy = np.load(r"0.npy")
print(npy.shape)
np.savez_compressed(r"0.npz",array=npy)
npz = np.load(r"0.npz")["array"]
