import numpy as np

def count_high_p(filepath):
    data = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    start_index = 0
    for i, line in enumerate(lines):
        if "ITEM: CELLS" in line:
            start_index = i + 1
            break
            
    for line in lines[start_index:]:
        parts = line.split()
        if len(parts) >= 11:
            row = [float(x) for x in parts[1:]]
            T = row[8]
            nrho = row[9]
            k_B = 1.380649e-23
            p = nrho * k_B * T
            data.append(p)
            
    data = np.array(data)
    print("Total cells:", len(data))
    print("Cells with p > 500 Pa:", np.sum(data > 500.0))
    print("Cells with p > 1000 Pa:", np.sum(data > 1000.0))
    print("Cells with p > 5000 Pa:", np.sum(data > 5000.0))
    print("Cells with p > 10000 Pa:", np.sum(data > 10000.0))

count_high_p("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/results_reference/grid.1100.out")
