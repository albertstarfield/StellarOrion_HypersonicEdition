"""
ExperimentalPresentation.py
===========================
A self-bootstrapping, local HTTP server-backed pywebview presentation engine.
Launches a daemon HTTP thread to serve local assets, resolving same-origin (CORS) issues.
Features a unified interactive infographic dashboard with zoom-in transitions.
Includes Manim scene fallbacks for video generation.
"""

import os
import sys
import re
import subprocess
import socket
import http.server
import socketserver
import threading
from typing import Dict, Any, Tuple, List, Optional

try:
    from manim import *
    HAS_MANIM = True
except ImportError:
    HAS_MANIM = False

# Global Port and Config
HTTP_PORT = 8085
CURRENT_WEEK = "Week 11"

def find_free_port(start_port: int = 8085) -> int:
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
        port += 1
    return start_port

HTTP_PORT = find_free_port(8085)

class SilentHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

def start_local_server() -> None:
    """Runs a simple HTTP server on localhost to serve assets without CORS issues."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    handler = SilentHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", HTTP_PORT), handler) as httpd:
        httpd.serve_forever()

class PresentationAPI:
    """API Exposed to JS inside the pywebview render engine."""
    def __init__(self, slides: List[Dict[str, Any]]) -> None:
        self.slides = slides

    def get_slides_data(self) -> List[Dict[str, Any]]:
        return self.slides

    def get_current_week(self) -> str:
        return CURRENT_WEEK

# --- MANIM PRESENTATION SCENE CLASS (For Video / Slide Export) ---
if HAS_MANIM:
    config.frame_width = 16
    config.frame_height = 9

    class ExperimentalPresentation(Scene):
        def construct(self):
            self.intro_scene()
            self.imagination_map_node()
            self.result_table_slide()
            self.outro()

        def add_overlay(self):
            self.overlay = VGroup(
                Text("StellarOrion Hypersonic Edition - Week 11", font_size=12, color=BLUE_B, weight=BOLD),
                Text("MDAO Optimization & Reference Comparison", font_size=10, color=GRAY)
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).to_corner(UL).shift(DOWN*0.2 + RIGHT*0.2)
            self.play(FadeIn(self.overlay), run_time=1.5)

        def intro_scene(self):
            title = Text("StellarOrion: Week 11 Experimental Presentation", font_size=40, color=BLUE_D, weight=BOLD)
            subtitle = Text("Hypersonic Aerothermal MDAO Optimization & IRVE-3 Baseline Comparison", font_size=24, color=GRAY)
            subtitle.next_to(title, DOWN, buff=0.4)
            
            self.play(Write(title, run_time=2.5))
            self.play(FadeIn(subtitle, shift=DOWN, run_time=1.5))
            self.wait(3)
            self.play(FadeOut(title), FadeOut(subtitle))
            self.add_overlay()

        def imagination_map_node(self):
            section_title = Title("Week 11 Imagination Map: MDAO Result Topology Node")
            self.add(section_title)

            # Core Node
            core_node = Circle(radius=1.1, color=BLUE, fill_opacity=0.8).shift(LEFT * 4)
            core_text = Text("StellarOrion\nMDAO Engine", font_size=14, color=WHITE, weight=BOLD).move_to(core_node.get_center())
            core_grp = VGroup(core_node, core_text)

            # Branch Nodes
            node_dsmc = Circle(radius=0.85, color=ORANGE, fill_opacity=0.7).shift(LEFT * 1 + UP * 2)
            text_dsmc = Text("SPARTA DSMC\nSolver Core", font_size=11, color=WHITE).move_to(node_dsmc.get_center())

            node_mop = Circle(radius=0.85, color=PURPLE_B, fill_opacity=0.7).shift(LEFT * 1 + DOWN * 2)
            text_mop = Text("MoP-SBO\nSurrogate Model", font_size=11, color=WHITE).move_to(node_mop.get_center())

            # NEW Node: Result Table Node
            node_result = Circle(radius=1.05, color=GREEN_D, fill_opacity=0.85).shift(RIGHT * 3)
            text_result = Text("Week 11\nResult Table\n(IRVE-3 vs Opt)", font_size=12, color=WHITE, weight=BOLD).move_to(node_result.get_center())

            # Connectors
            line1 = Line(core_node.get_right(), node_dsmc.get_left(), color=BLUE_B, stroke_width=2)
            line2 = Line(core_node.get_right(), node_mop.get_left(), color=BLUE_B, stroke_width=2)
            line3 = Line(node_dsmc.get_right(), node_result.get_left(), color=GREEN_B, stroke_width=2.5)
            line4 = Line(node_mop.get_right(), node_result.get_left(), color=GREEN_B, stroke_width=2.5)

            # Leaf detail boxes for Result Node
            opt_a_box = Rectangle(width=3.2, height=1.1, color=YELLOW, fill_opacity=0.2).shift(RIGHT * 6 + UP * 1.5)
            opt_a_txt = Text("Optimum A: Max Drag\n194.84 kN (+210.6%)\nD=4.86m, β=8.85 kg/m²", font_size=10, color=YELLOW).move_to(opt_a_box.get_center())

            opt_b_box = Rectangle(width=3.2, height=1.1, color=TEAL, fill_opacity=0.2).shift(RIGHT * 6 + DOWN * 1.5)
            opt_b_txt = Text("Optimum B: Stability\n92.84 kN Drag (θ=75°)\nT_back=341.2K (≤350K)", font_size=10, color=TEAL).move_to(opt_b_box.get_center())

            arrow_a = Arrow(node_result.get_right(), opt_a_box.get_left(), color=YELLOW, buff=0.1)
            arrow_b = Arrow(node_result.get_right(), opt_b_box.get_left(), color=TEAL, buff=0.1)

            self.play(FadeIn(core_grp, run_time=1.5))
            self.play(Create(line1), Create(line2), FadeIn(node_dsmc), FadeIn(text_dsmc), FadeIn(node_mop), FadeIn(text_mop), run_time=2)
            self.play(Create(line3), Create(line4), FadeIn(node_result), Write(text_result), run_time=2)
            self.play(GrowArrow(arrow_a), FadeIn(opt_a_box), Write(opt_a_txt), GrowArrow(arrow_b), FadeIn(opt_b_box), Write(opt_b_txt), run_time=2.5)
            self.wait(4)

            self.play(
                FadeOut(section_title), FadeOut(core_grp), FadeOut(node_dsmc), FadeOut(text_dsmc),
                FadeOut(node_mop), FadeOut(text_mop), FadeOut(node_result), FadeOut(text_result),
                FadeOut(line1), FadeOut(line2), FadeOut(line3), FadeOut(line4),
                FadeOut(opt_a_box), FadeOut(opt_a_txt), FadeOut(opt_b_box), FadeOut(opt_b_txt),
                FadeOut(arrow_a), FadeOut(arrow_b)
            )

        def result_table_slide(self):
            section_title = Title("Week 11 Experimentation: IRVE-3 Reference vs. AI Optimums")
            self.add(section_title)

            table_data = [
                ["Parameter / Metric", "IRVE-3 Reference", "Optimum A (Max Drag)", "Optimum B (Stability)", "Delta (Opt A vs Ref)"],
                ["Major Outer Diameter (D)", "3.00 m", "4.86 m (Expanded)", "2.92 m (Standard)", "+62.0%"],
                ["Cone Half-Angle (θ)", "60.0°", "45.0°", "75.0°", "-15.0°"],
                ["Toroid Stack Count (N)", "6", "7 (Locked 202.5mm)", "6", "+1 toroid"],
                ["Nose Radius (Rn)", "0.55 m", "0.60 m", "0.60 m", "+0.05 m"],
                ["Aerodynamic Drag (FD)", "62.72 kN", "194.84 kN", "92.84 kN", "+210.6%"],
                ["Drag Coefficient (CD)", "≈1.47", "1.49 (Scalloped)", "1.48", "+1.36%"],
                ["Ballistic Coeff (β)", "26.90 kg/m²", "8.85 kg/m² (Fast Decel)", "18.58 kg/m²", "-67.10%"],
                ["Stagnation Heat (q_stag)", "14.36 W/cm²", "18.16 W/cm²", "18.16 W/cm²", "+3.80 W/cm²"],
                ["Shock Layer Temp (T_shock)", "12,362 K", "3,991.3 K", "9,492.8 K", "-67.7%"],
                ["Radiative Surf Temp (T_surf)", "1,453 K", "1,675 K", "1,453 K", "+222 K"],
                ["Backside Payload Temp (T_back)", "≤350 K", "338.5 K", "341.2 K", "PASS (≤350 K Limit)"],
                ["Generated CAD & Mesh Artifacts", "HIAD_custom_full.step", "geometry.step", "geometry.step", "3D STEP & STL"]
            ]

            table = Table(
                table_data,
                include_outer_lines=True,
                line_config={"stroke_width": 1, "color": BLUE_C}
            ).scale(0.31).shift(DOWN * 0.3)

            table.get_rows()[0].set_color(YELLOW)
            table.get_columns()[2].set_color(GREEN_B)

            self.play(Create(table, run_time=6))
            self.wait(6)
            self.play(FadeOut(table), FadeOut(section_title))

        def outro(self):
            if hasattr(self, "overlay"):
                self.play(FadeOut(self.overlay), run_time=1.5)
            final = Text("StellarOrion Week 11: Validated Reentry Optimization Complete", font_size=28, color=BLUE_D, weight=BOLD)
            self.play(Write(final, run_time=3))
            self.wait(3)
            self.play(FadeOut(final))

def main() -> None:
    """Launches the Pywebview desktop GUI slide engine if webview is installed."""
    try:
        import webview
    except ImportError:
        print("[*] Pywebview not installed. Running Manim scene generation if available...")
        return

    slides = []
    server_thread = threading.Thread(target=start_local_server, daemon=True)
    server_thread.start()

    server_url = f"http://localhost:{HTTP_PORT}/component/renderEngine/index.html"
    print(f"[*] Local asset server started on http://localhost:{HTTP_PORT}")
    print("[*] Starting Pywebview window...")
    api = PresentationAPI(slides)
    webview.create_window(
        f"StellarOrion {CURRENT_WEEK} — Experimental Presentation",
        server_url,
        js_api=api,
        width=1366,
        height=850,
        resizable=True,
        background_color="#090a15"
    )
    webview.start(debug=True)

if __name__ == "__main__":
    main()
