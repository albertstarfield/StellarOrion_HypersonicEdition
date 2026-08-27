import numpy as np

def analyze(filepath):
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
            xc = (row[0] + row[2]) / 2.0
            yc = (row[1] + row[3]) / 2.0
            u = row[5]
            v = row[6]
            T = row[8]
            nrho = row[9]
            
            m_avg = 28.97e-3 / 6.022e23
            rho = nrho * m_avg
            k_B = 1.380649e-23
            p = nrho * k_B * T
            
            data.append([xc, yc, rho, u, v, T, p])
            
    data = np.array(data)
    
    non_zero = data[data[:, 6] > 1e-3]
    print("Total parsed cells:", len(data))
    print("Non-zero cells:", len(non_zero))
    
    max_p_idx = np.argmax(data[:, 6])
    print(f"Max Press Cell: Coords={data[max_p_idx, :2]} p={data[max_p_idx, 6]:.2f} Pa, T={data[max_p_idx, 5]:.2f} K")
    
    max_t_idx = np.argmax(data[:, 5])
    print(f"Max Temp Cell: Coords={data[max_t_idx, :2]} p={data[max_t_idx, 6]:.2f} Pa, T={data[max_t_idx, 5]:.2f} K")
    
    # Analyze stagnation line (y <= 0.05)
    stag_line = data[data[:, 1] <= 0.05]
    # Sort by x
    stag_line = stag_line[np.argsort(stag_line[:, 0])]
    print("\nStagnation line profile (subset):")
    print(f"{'x':<10} | {'y':<10} | {'rho':<12} | {'u':<10} | {'T':<10} | {'p':<10}")
    print("-" * 72)
    # Print every 20th point or so to see the profile
    for i in range(0, len(stag_line), max(1, len(stag_line)//20)):
        row = stag_line[i]
        print(f"{row[0]:.4f} | {row[1]:.4f} | {row[2]:.2e} | {row[3]:.1f} | {row[5]:.1f} | {row[6]:.1f}")

analyze("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/results_reference/grid.1100.out")
