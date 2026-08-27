import numpy as np

def analyze_stagnation_region(filepath):
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
            # id xlo ylo xhi yhi f_2[*] f_3[*] f_4[*]
            # index mappings:
            # parts[0]: cell_id
            # parts[1]: xlo
            # parts[2]: ylo
            # parts[3]: xhi
            # parts[4]: yhi
            # parts[5]: f_2[1] (u)
            # parts[6]: f_2[2] (v)
            # parts[7]: f_2[3] (w)
            # parts[8]: f_3[1] (temp)
            # parts[9]: f_4[1] (nrho)
            # parts[10]: f_4[2] (rho) -> wait, let's verify if parts[10] is rho or if pressure is nrho * k_B * T
            x = 0.5 * (row[0] + row[2])
            y = 0.5 * (row[1] + row[3])
            T = row[8]
            nrho = row[9]
            k_B = 1.380649e-23
            p = nrho * k_B * T
            data.append((x, y, T, nrho, p))
            
    data = np.array(data)
    
    # Let's filter for x < 0.1 and y < 0.2
    idx_stag = np.where((data[:, 0] < 0.1) & (data[:, 1] < 0.2))[0]
    stag_data = data[idx_stag]
    
    # Sort by pressure descending
    stag_data_sorted = stag_data[np.argsort(stag_data[:, 4])[::-1]]
    
    print("Top 10 highest pressure cells in stagnation region (x < 0.1, y < 0.2):")
    print(f"{'X':<8} | {'Y':<8} | {'T (K)':<8} | {'nrho (1/m3)':<12} | {'P (Pa)':<8}")
    print("-" * 55)
    for i in range(min(10, len(stag_data_sorted))):
        x, y, T, nrho, p = stag_data_sorted[i]
        print(f"{x:.4f}  | {y:.4f}  | {T:.1f}   | {nrho:.4e}   | {p:.1f}")

analyze_stagnation_region("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/results_reference/grid.1100.out")
