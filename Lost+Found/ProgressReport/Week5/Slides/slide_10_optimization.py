def get_slide_data() -> dict:
    return {
        'title': 'Optimization Parameters & Targets',
        'content': r"""
# Multi-Disciplinary Optimization (MDO) Parameters

Why are we targeting these specific variables?

## Design Variables from Rapisarda MDAO Reference

| Parameter | Symbol | Range | Why Target This? |
| :--- | :--- | :--- | :--- |
| **Half-Cone Angle** | $\theta$ | $40° - 80°$ | Controls the **drag-to-heating ratio**. Shallower angles reduce drag but increase heat flux; steeper angles increase drag but risk flow separation. |
| **Number of Tori** | $N$ | $1 - 9$ | More tori = larger deployed diameter = **lower ballistic coefficient**. Diminishing returns beyond $N=6$. |
| **Inner Tori Radius** | $r_{\text{torus}}$ | $0.01\text{m} - 0.5\text{m}$ | Directly affects **boundary layer thickness** and **scallop pocket heating** between adjacent tori. |
| **Outer Torus Radius** | $r_{\text{out}}$ | $r_{\text{torus}} > r_{\text{out}}$ | Governs **flow separation** at the shoulder. |

---

<div style="background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 16px; padding: 1.5rem; margin: 1.5rem 0; box-shadow: 0 12px 32px rgba(0,0,0,0.6);">
    <h3 style="color: #06b6d4; font-weight: 600; margin-top: 0; margin-bottom: 1.2rem; display: flex; align-items: center; gap: 0.5rem;">
        ⚡ MoP SBO Multi-Disciplinary Optimization Flowchart
    </h3>
    <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: rgba(30, 41, 59, 0.9); border: 1.5px solid #06b6d4; border-radius: 12px; padding: 1rem 1.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2);">
            <div>
                <div style="font-weight: 700; color: #38bdf8; font-size: 1rem;">1. SPARTA DSMC Ground Truth Sampling</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem;">25 CCD / LHS geometry variants × 1,100 SPARTA timesteps</div>
            </div>
            <span style="background: rgba(14, 165, 233, 0.2); border: 1px solid #38bdf8; color: #38bdf8; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.78rem; font-family: monospace; font-weight: 600; white-space: nowrap;">⏱️ ~20-24 Hours Wall-Clock</span>
        </div>
        <div style="text-align: center; color: #06b6d4; font-size: 1.2rem; margin: -0.4rem 0;">▼</div>
        <div style="background: rgba(30, 41, 59, 0.9); border: 1.5px solid #a855f7; border-radius: 12px; padding: 1rem 1.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(168, 85, 247, 0.2);">
            <div>
                <div style="font-weight: 700; color: #c084fc; font-size: 1rem;">2. Train MoP DeepXDE PINN Metamodel</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem;">Learns continuous response surface + enforces Navier-Stokes PDE loss (2,500 epoch steps)</div>
            </div>
            <span style="background: rgba(168, 85, 247, 0.2); border: 1px solid #c084fc; color: #c084fc; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.78rem; font-family: monospace; font-weight: 600; white-space: nowrap;">⏱️ ~11 Mins GPU/CPU</span>
        </div>
        <div style="text-align: center; color: #a855f7; font-size: 1.2rem; margin: -0.4rem 0;">▼</div>
        <div style="background: rgba(30, 41, 59, 0.9); border: 1.5px solid #f59e0b; border-radius: 12px; padding: 1rem 1.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.2);">
            <div>
                <div style="font-weight: 700; color: #fbbf24; font-size: 1rem;">3. SBO Evolutionary Loop (NSGA-II Genetic Search)</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem;">Evaluates 10,000 to 20,000 candidate shapes using MoP surrogate ──► Extracts PARETO FRONTIER</div>
            </div>
            <span style="background: rgba(245, 158, 11, 0.2); border: 1px solid #fbbf24; color: #fbbf24; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.78rem; font-family: monospace; font-weight: 600; white-space: nowrap;">⏱️ ~5 ms / eval (&lt; 10s)</span>
        </div>
        <div style="text-align: center; color: #f59e0b; font-size: 1.2rem; margin: -0.4rem 0;">▼</div>
        <div style="background: rgba(30, 41, 59, 0.9); border: 1.5px solid #10b981; border-radius: 12px; padding: 1rem 1.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);">
            <div>
                <div style="font-weight: 700; color: #34d399; font-size: 1rem;">4. Final Pareto Winner Verification</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.2rem;">Selects Variant #24 (-38.2% peak heat flux) for 1 final extended (10,000+ step) DSMC run</div>
            </div>
            <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #34d399; color: #34d399; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.78rem; font-family: monospace; font-weight: 600; white-space: nowrap;">🎯 Final Verification</span>
        </div>
    </div>
</div>
"""
    }
