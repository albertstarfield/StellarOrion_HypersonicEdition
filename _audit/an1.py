from PIL import Image
import numpy as np
p = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/Lost+Found/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png"
im = Image.open(p).convert("RGB")
a = np.asarray(im).astype(int)
print("size", im.size)
cols, counts = np.unique(a.reshape(-1, 3), axis=0, return_counts=True)
idx = np.argsort(-counts)[:20]
for i in idx:
    print(cols[i], counts[i])
