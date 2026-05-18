from manim import *
import numpy as np

# Config for high quality
config.frame_width = 16
config.frame_height = 9

class DSMCVisualization(Scene):
    def construct(self):
        self.intro_scene()
        self.preprocessing_geometry()
        self.scalloping_and_wake()
        self.preprocessing_grid()
        self.solver_intro()
        self.timestep_move()
        self.timestep_migrate()
        self.timestep_sort()
        self.timestep_collide()
        self.timestep_chemistry()
        self.post_processing()
        self.pinn_refinement()
        self.survivability_optimization()
        self.outro()

    def add_overlay(self):
        self.overlay = VGroup(
            Text("StellarOrion Hypersonic EditioN", font_size=12, color=BLUE_B, weight=BOLD),
            Text("Git Commit: 76a0c73", font_size=10, color=GRAY)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).to_corner(UL).shift(DOWN*0.2 + RIGHT*0.2)
        self.play(FadeIn(self.overlay), run_time=2)

    def intro_scene(self):
        title = Text("StellarOrion Hypersonic Edition", font_size=48, color=BLUE_D)
        subtitle = Text("SPARTA DSMC Full Workflow Visualization", font_size=32, color=GRAY)
        subtitle.next_to(title, DOWN, buff=0.5)
        
        self.play(Write(title, run_time=3))
        self.play(FadeIn(subtitle, shift=DOWN, run_time=2))
        self.wait(5)
        self.play(FadeOut(title), FadeOut(subtitle))
        self.add_overlay()

    def preprocessing_geometry(self):
        section_title = Title("1. Preprocessing: Geometry Generation")
        self.add(section_title)
        
        # HIAD Parameters
        params = VGroup(
            MathTex(r"\text{Diameter } (D) = 3.0\,m"),
            MathTex(r"\text{Angle } (\theta_c) = 60^\circ"),
            MathTex(r"\text{Toroids } (N) = 7"),
            MathTex(r"\text{Nose Radius } (r_N) = 0.55\,m")
        ).arrange(DOWN, aligned_edge=LEFT).scale(0.8).to_edge(LEFT)
        
        self.play(Create(params, run_time=4))
        
        # Analytical HIAD Shape
        nose = Arc(radius=1.5, start_angle=-PI/3, angle=2*PI/3, color=RED)
        line1 = Line(start=nose.get_start(), end=nose.get_start() + [3, -1.5*np.tan(PI/6), 0], color=RED)
        line2 = Line(start=nose.get_end(), end=nose.get_end() + [3, 1.5*np.tan(PI/6), 0], color=RED)
        hiad_shape = VGroup(nose, line1, line2).scale(1.2).shift(RIGHT*2)
        
        self.play(Create(hiad_shape, run_time=5))
        self.wait(5)
        
        # Analytical equations to display
        eq_nose = MathTex(r"r_N = \frac{r_{pay}}{\cos(\theta_c)} \quad \text{(Eq. 3.4) [Rapisarda, 2023]}").scale(0.8)
        eq_radius = MathTex(r"R_{inf} = 2 r_t N \sin(\theta_c) + 2 r_{out} \sin(\theta_c) + 2 r_t (1 - \sin(\theta_c)) + r_N \cos(\theta_c) \quad \text{(Eq. 3.3) [Lau, 2013]}").scale(0.62)
        eq_group = VGroup(eq_nose, eq_radius).arrange(DOWN, buff=0.25).to_edge(UP).shift(DOWN*0.9)
        self.play(Write(eq_nose, run_time=3))
        self.play(Write(eq_radius, run_time=4))
        self.wait(5)
        
        self.play(FadeOut(params), FadeOut(hiad_shape), FadeOut(eq_group), FadeOut(section_title))

    def scalloping_and_wake(self):
        section_title = Title("1B. Topology and Wake: Scalloped vs. Smooth")
        self.add(section_title)
        
        # Titles for comparison
        smooth_lbl = Text("Smooth Shield (Idealized)", font_size=20, color=BLUE_A).shift(LEFT*4 + UP*2)
        scallop_lbl = Text("Scalloped Shield (Stacked Toroids)", font_size=20, color=ORANGE).shift(RIGHT*4 + UP*2)
        self.play(Write(smooth_lbl), Write(scallop_lbl), run_time=2)
        
        # Smooth geometry on the left
        smooth_nose = Arc(radius=1.0, start_angle=-PI/3, angle=2*PI/3, color=BLUE_D).scale(0.8).shift(LEFT*4 + DOWN*0.5)
        smooth_cone1 = Line(smooth_nose.get_start(), smooth_nose.get_start() + [1.5, -0.866, 0], color=BLUE_D)
        smooth_cone2 = Line(smooth_nose.get_end(), smooth_nose.get_end() + [1.5, 0.866, 0], color=BLUE_D)
        smooth_shield = VGroup(smooth_nose, smooth_cone1, smooth_cone2)
        
        # Scalloped geometry on the right (stacked toroids) - showing inflation dynamics
        scalloped_nose = Arc(radius=1.0, start_angle=-PI/3, angle=2*PI/3, color=ORANGE).scale(0.8).shift(RIGHT*4 + DOWN*0.5)
        
        # Create uninflated (packed) toroids group
        uninflated_toroids = VGroup()
        for idx in range(4):
            uninflated_toroids.add(Circle(radius=0.02, color=RED_E, fill_opacity=0.3).shift(RIGHT*4 + [0.4, 0.1*idx, 0]))
            uninflated_toroids.add(Circle(radius=0.02, color=RED_E, fill_opacity=0.3).shift(RIGHT*4 + [0.4, -0.1*idx, 0]))
            
        inflation_lbl = Text("Inflation: P = 300 kPa", font_size=16, color=YELLOW).shift(RIGHT*4 + UP*1.2)
        
        self.play(Create(smooth_shield), Create(scalloped_nose), Create(uninflated_toroids), run_time=3)
        self.play(Write(inflation_lbl), run_time=1.5)
        
        # Animate the toroids inflating (scaling up and moving to their final stacked positions)
        inflated_toroids = VGroup()
        for idx in range(4):
            # top toroids
            inflated_toroids.add(Circle(radius=0.18, color=RED_E, fill_opacity=0.3).shift(RIGHT*4 + [0.8 + idx*0.35, 0.5 + idx*0.2, 0]))
            # bottom toroids
            inflated_toroids.add(Circle(radius=0.18, color=RED_E, fill_opacity=0.3).shift(RIGHT*4 + [0.8 + idx*0.35, -0.5 - idx*0.2, 0]))
            
        self.play(Transform(uninflated_toroids, inflated_toroids), run_time=3)
        scalloped_shield = VGroup(scalloped_nose, uninflated_toroids)
        self.play(FadeOut(inflation_lbl), run_time=1)
        
        # Flow simulation on smooth shield
        smooth_particles = VGroup(*[Dot(radius=0.04, color=BLUE_A).move_to(LEFT*6.5 + [0, y, 0]) for y in np.linspace(-1.5, 1.5, 8)])
        self.play(FadeIn(smooth_particles), run_time=1)
        # Particles flow cleanly around smooth shield
        smooth_paths = []
        for p in smooth_particles:
            y_val = p.get_center()[1]
            sign = np.sign(y_val) if y_val != 0 else 1
            smooth_paths.append(p.animate.move_to(LEFT*1.5 + [2.0, y_val + sign*0.8, 0]))
        self.play(*smooth_paths, run_time=4)
        
        # Flow simulation on scalloped shield (crests hotspots & valley vortices)
        scallop_particles = VGroup(*[Dot(radius=0.04, color=YELLOW).move_to(RIGHT*1.5 + [0, y, 0]) for y in np.linspace(-1.5, 1.5, 8)])
        self.play(FadeIn(scallop_particles), run_time=1)
        # Some hit crests (turn RED) and some recirculate in valleys
        scallop_paths = []
        for idx, p in enumerate(scallop_particles):
            y_val = p.get_center()[1]
            sign = np.sign(y_val) if y_val != 0 else 1
            if idx in [1, 2, 5, 6]: # hit the toroid valleys/crests
                scallop_paths.append(p.animate.move_to(RIGHT*4.8 + [0.6, y_val*0.6, 0]).set_color(RED))
            else:
                scallop_paths.append(p.animate.move_to(RIGHT*6.5 + [1.5, y_val + sign*1.2, 0]))
        self.play(*scallop_paths, run_time=4)
        
        # Display the scalloping penalty finding
        penalty_text = VGroup(
            Text("Crests act as micro-stagnation points (+30% local heating)", font_size=16, color=RED),
            Text("Valleys generate recirculating vortices and heat accumulation", font_size=16, color=ORANGE),
            Text("SBO thickens F-TPS locally in valleys to maintain safety (<350K)", font_size=16, color=GREEN)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_edge(DOWN).shift(UP*0.2)
        
        self.play(Create(penalty_text, run_time=5))
        self.wait(5)
        
        # Clean up comparison
        self.play(
            FadeOut(smooth_shield), FadeOut(scalloped_shield), 
            FadeOut(smooth_particles), FadeOut(scallop_particles),
            FadeOut(smooth_lbl), FadeOut(scallop_lbl), FadeOut(penalty_text)
        )
        
        # --- Aftbody Wake Recirculation (The Backshell Heating Problem) ---
        wake_title = Title("1C. Aftbody Wake Flow: The Recirculation Vortex")
        self.play(Transform(section_title, wake_title), run_time=2)
        
        # Full shield in the center (moving left slightly)
        shield = VGroup(
            Arc(radius=1.5, start_angle=-PI/3, angle=2*PI/3, color=ORANGE).scale(0.8),
            Line([-1.2, -0.65, 0], [0.5, -1.8, 0], color=ORANGE),
            Line([-1.2, 0.65, 0], [0.5, 1.8, 0], color=ORANGE)
        ).shift(LEFT*3)
        
        # Payload behind the shield
        payload = Rectangle(width=1.5, height=1.0, color=GRAY, fill_opacity=0.4).shift(LEFT*1.8)
        payload_lbl = Text("Payload (Electronics/Crew)", font_size=14, color=WHITE).next_to(payload, DOWN, buff=0.1)
        
        self.play(Create(shield), Create(payload), Write(payload_lbl), run_time=2)
        
        # Recirculating wake particles
        wake_particles = VGroup(*[Dot(radius=0.03, color=PURPLE).move_to([1.5, np.random.uniform(-1.0, 1.0), 0]) for _ in range(50)])
        self.play(FadeIn(wake_particles), run_time=2)
        
        # Show them forming a large swirling recirculating vortex behind the shield
        recirc_paths = []
        for p in wake_particles:
            c = p.get_center()
            # Calculate a circular path in the wake
            recirc_paths.append(p.animate.move_to([c[0] - 1.2, c[1]*0.5, 0]).set_color(DARK_BLUE))
        self.play(*recirc_paths, run_time=4)
        
        # Add swirling rotation with DDES scale-resolving turbulence fluctuations
        turb_lbl = Text("DDES Scale-Resolving Unsteady Wake", font_size=18, color=YELLOW).to_edge(DOWN).shift(RIGHT*2.5 + UP*0.5)
        self.play(Write(turb_lbl), run_time=1.5)
        
        # Apply a semi-random chaotic deviation to each particle while rotating to simulate DDES turbulence
        def make_turbulent(mobject):
            for d in mobject:
                d.shift(np.random.normal(0, 0.08, 3))
        
        wake_particles.add_updater(make_turbulent)
        self.play(Rotate(wake_particles, angle=PI*1.5, about_point=RIGHT*0.2, run_time=6))
        wake_particles.remove_updater(make_turbulent)
        self.play(FadeOut(turb_lbl), run_time=1)
        
        wake_info = VGroup(
            Text("Low-Density Rarefied Wake Recirculation Zone (Kn > 0.05)", font_size=18, color=PURPLE),
            Text("Unsteady fluctuations resolved by DDES (Delayed Detached-Eddy)", font_size=18, color=BLUE_A),
            Text("VUV Radiation dominates lee-side backshell heating at lunar entry", font_size=18, color=RED)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_edge(UP).shift(DOWN*0.95 + RIGHT*2.5).scale(0.8)
        
        self.play(Create(wake_info, run_time=5))
        self.wait(5)
        
        # Clean up Section
        self.play(
            FadeOut(shield), FadeOut(payload), FadeOut(payload_lbl), 
            FadeOut(wake_particles), FadeOut(wake_info), FadeOut(section_title)
        )

    def preprocessing_grid(self):
        section_title = Title("2. Preprocessing: Grid Generation")
        self.add(section_title)
        
        # Domain rectangle
        domain = Rectangle(width=10, height=6, color=WHITE, stroke_width=2)
        self.play(Create(domain, run_time=3))
        
        # Initial Grid (Coarse)
        grid = VGroup(*([Line([x, -3, 0], [x, 3, 0]) for x in np.linspace(-5, 5, 11)] + 
                       [Line([-5, y, 0], [5, y, 0]) for y in np.linspace(-3, 3, 7)]))
        grid.set_stroke(BLUE, width=0.5, opacity=0.3)
        self.play(Create(grid, run_time=5))
        
        # Body Overlay
        body = Circle(radius=1, color=RED, fill_opacity=0.2).shift(LEFT*2)
        self.play(FadeIn(body, run_time=2))
        
        # Adaptive Refinement
        refined_grid = VGroup()
        for x in np.linspace(-3, -1, 10):
            for y in np.linspace(-1, 1, 10):
                refined_grid.add(Rectangle(width=0.2, height=0.2, color=BLUE_A, stroke_width=0.2).move_to([x, y, 0]))
        
        self.play(Create(refined_grid, run_time=8))
        
        logic = Text("Cell Size < Mean Free Path (λ)", font_size=24, color=YELLOW).to_edge(DOWN)
        self.play(Write(logic, run_time=3))
        self.wait(10)
        
        self.play(FadeOut(domain), FadeOut(grid), FadeOut(body), FadeOut(refined_grid), FadeOut(logic), FadeOut(section_title))

    def solver_intro(self):
        section_title = Title("3. SPARTA DSMC Solver: The Kinetic Engine")
        self.add(section_title)
        
        boltzmann = MathTex(r"\frac{\partial f}{\partial t} + \mathbf{v} \cdot \nabla f + \frac{\mathbf{F}}{m} \cdot \nabla_\mathbf{v} f = \left( \frac{\partial f}{\partial t} \right)_{coll} \quad \text{[Bird, 1994]}")
        boltzmann.scale(1.1).shift(UP)
        
        desc = Text("Modeling gas as discrete representative particles [Plimpton & Gallis, 2014]", font_size=20, color=GRAY).next_to(boltzmann, DOWN)
        
        self.play(Write(boltzmann, run_time=5))
        self.play(FadeIn(desc, run_time=3))
        self.wait(5)
        
        # Fill with particles
        particles = VGroup(*[Dot(radius=0.03, color=WHITE).move_to([np.random.uniform(-5, 5), np.random.uniform(-3, 3), 0]) for _ in range(200)])
        self.play(FadeIn(particles, run_time=4))
        self.wait(5)
        
        self.play(FadeOut(boltzmann), FadeOut(desc), FadeOut(particles), FadeOut(section_title))

    def timestep_move(self):
        section_title = Title("Timestep Loop: 1. Move and Reflect (Knudsen Boundary)")
        self.add(section_title)
        
        # Screen splitter
        splitter = DashedLine([0, 2.5, 0], [0, -3, 0], color=GRAY)
        self.play(Create(splitter), run_time=1.5)
        
        # Labels for comparison
        lbl_left = Text("Continuum: No-Slip (Kn -> 0)", font_size=18, color=BLUE_A).shift(LEFT*4 + UP*2)
        lbl_right = Text("Rarefied: Slip-Flow (Kn > 0.01)", font_size=18, color=ORANGE).shift(RIGHT*4 + UP*2)
        self.play(Write(lbl_left), Write(lbl_right), run_time=2)
        
        # Left boundary (No-slip, Maxwellian diffuse reflection)
        body_left = Line([-4, -2.5, 0], [0, -2.5, 0], color=RED, stroke_width=4)
        p_left = Dot(color=YELLOW).move_to([-2, 1.5, 0])
        vel_left = Arrow(start=[-2, 1.5, 0], end=[-2, -2.5, 0], color=BLUE, buff=0)
        
        # Right boundary (Slip-flow boundary & Temperature Jump)
        body_right = Line([0, -2.5, 0], [4, -2.5, 0], color=RED, stroke_width=4)
        p_right = Dot(color=YELLOW).move_to([2, 1.5, 0])
        vel_right = Arrow(start=[2, 1.5, 0], end=[2.5, -2.5, 0], color=BLUE, buff=0)
        
        self.play(
            Create(body_left), Create(body_right),
            FadeIn(p_left), FadeIn(p_right),
            GrowArrow(vel_left), GrowArrow(vel_right),
            run_time=2
        )
        
        # 1. Particles move to wall
        self.play(
            p_left.animate.move_to([-2, -2.5, 0]),
            p_right.animate.move_to([2.5, -2.5, 0]),
            vel_left.animate.put_start_and_end_on([-2, -2.5, 0], [-2, -2.5, 0]),
            vel_right.animate.put_start_and_end_on([2.5, -2.5, 0], [2.5, -2.5, 0]),
            run_time=3
        )
        
        # Show specific reflection dynamics
        desc_left = Text("No tangential velocity: u_slip = 0\nDiffuse Maxwellian reflection", font_size=12, color=BLUE_B).shift(LEFT*4 + DOWN*1.5)
        desc_right = MathTex(r"u_{slip} = \frac{2-\sigma_v}{\sigma_v} \lambda \frac{\partial u}{\partial y} > 0 \quad \text{(Eq. 2.1)}\\\text{Temperature Jump (Higher } T_{reflected}\text{)}").scale(0.5).shift(RIGHT*4 + DOWN*1.5)
        
        self.play(Write(desc_left), Write(desc_right), run_time=3)
        
        # Recreate arrows for reflection
        ref_vel_left = Arrow(start=[-2, -2.5, 0], end=[-1.5, 0, 0], color=ORANGE, buff=0)
        ref_vel_right = Arrow(start=[2.5, -2.5, 0], end=[3.8, -1.0, 0], color=RED, buff=0)
        
        # 2. Reflect particles
        self.play(
            p_left.animate.move_to([-1.5, 0, 0]),
            p_right.animate.move_to([3.8, -1.0, 0]),
            GrowArrow(ref_vel_left),
            GrowArrow(ref_vel_right),
            run_time=3
        )
        self.wait(4)
        
        # Clean up
        self.play(
            FadeOut(splitter), FadeOut(lbl_left), FadeOut(lbl_right),
            FadeOut(body_left), FadeOut(body_right), FadeOut(p_left), FadeOut(p_right),
            FadeOut(vel_left), FadeOut(vel_right), FadeOut(ref_vel_left), FadeOut(ref_vel_right),
            FadeOut(desc_left), FadeOut(desc_right), FadeOut(section_title)
        )

    def timestep_migrate(self):
        section_title = Title("Timestep Loop: 2. Migrate (MPI Exchange)")
        self.add(section_title)
        
        # Split screen
        sep = DashedLine([0, 3, 0], [0, -3, 0], color=WHITE)
        label1 = Text("Processor 0", font_size=24).shift(LEFT*4 + UP*2)
        label2 = Text("Processor 1", font_size=24).shift(RIGHT*4 + UP*2)
        
        self.play(Create(sep), Write(label1), Write(label2), run_time=4)
        
        p = Dot(color=WHITE).move_to([-0.5, 0, 0])
        self.play(FadeIn(p))
        self.play(p.animate.move_to([0.5, 0, 0]), run_time=5)
        
        sync = Text("MPI_Send / MPI_Recv", font_size=24, color=BLUE_A).to_edge(DOWN)
        self.play(Write(sync, run_time=3))
        self.wait(5)
        
        self.play(FadeOut(sep), FadeOut(label1), FadeOut(label2), FadeOut(p), FadeOut(sync), FadeOut(section_title))

    def timestep_sort(self):
        section_title = Title("Timestep Loop: 3. Sort (Cache Optimization)")
        self.add(section_title)
        
        # Memory array
        slots = VGroup(*[Square(side_length=0.5, color=GRAY) for _ in range(10)]).arrange(RIGHT, buff=0.1)
        dots = VGroup(*[Dot(radius=0.15, color=c) for c in [RED, BLUE, RED, GREEN, BLUE, GREEN, RED, BLUE, GREEN, RED]])
        for i in range(10): dots[i].move_to(slots[i].get_center())
        
        self.play(Create(slots), FadeIn(dots), run_time=4)
        self.wait(2)
        
        # Sorting
        sorted_dots = VGroup(*[Dot(radius=0.15, color=c) for c in [RED, RED, RED, RED, BLUE, BLUE, BLUE, GREEN, GREEN, GREEN]])
        for i in range(10): sorted_dots[i].move_to(slots[i].get_center())
        
        self.play(Transform(dots, sorted_dots, run_time=6))
        
        desc = Text("Group by Cell ID for faster pairing", font_size=24, color=GRAY).to_edge(DOWN)
        self.play(Write(desc, run_time=3))
        self.wait(5)
        
        self.play(FadeOut(slots), FadeOut(dots), FadeOut(desc), FadeOut(section_title))

    def timestep_collide(self):
        section_title = Title("Timestep Loop: 4. Collide (VSS Model)")
        self.add(section_title)
        
        cell = Square(side_length=4, color=BLUE_E, fill_opacity=0.1)
        p1 = Dot(color=YELLOW).move_to([-1, 1, 0])
        p2 = Dot(color=ORANGE).move_to([1, -1, 0])
        v1 = Arrow(start=[-1, 1, 0], end=[0, 0.5, 0], color=YELLOW, buff=0)
        v2 = Arrow(start=[1, -1, 0], end=[0, -0.5, 0], color=ORANGE, buff=0)
        
        self.play(Create(cell, run_time=3), FadeIn(p1), FadeIn(p2), GrowArrow(v1), GrowArrow(v2))
        
        # Probability Equation
        prob = MathTex(r"P_{coll} \propto \sigma_T \cdot v_{rel}")
        prob.to_edge(RIGHT).shift(UP)
        self.play(Write(prob, run_time=3))
        
        # Collision
        self.play(p1.animate.move_to([0, 0, 0]), p2.animate.move_to([0, 0, 0]), 
                  v1.animate.put_start_and_end_on([0, 0, 0], [-1, -0.5, 0]),
                  v2.animate.put_start_and_end_on([0, 0, 0], [1, 0.5, 0]), run_time=6)
        
        self.play(p1.animate.move_to([-1, -0.5, 0]), p2.animate.move_to([1, 0.5, 0]), run_time=4)
        self.wait(5)
        
        self.play(FadeOut(cell), FadeOut(p1), FadeOut(p2), FadeOut(v1), FadeOut(v2), FadeOut(prob), FadeOut(section_title))

    def timestep_chemistry(self):
        section_title = Title("Timestep Loop: 5. Chemistry and Surface Catalysis")
        self.add(section_title)
        
        # --- Part 1: TCE Dissociation ---
        desc_tce = Text("1. TCE Molecular Dissociation (Gas Chemistry)", font_size=24, color=BLUE_A).to_edge(UP).shift(DOWN*0.9)
        self.play(Write(desc_tce, run_time=2))
        
        mol = VGroup(Dot(radius=0.2, color=RED), Dot(radius=0.2, color=RED)).arrange(RIGHT, buff=0.1).move_to(LEFT*2)
        collider = Dot(radius=0.1, color=WHITE).move_to(RIGHT*2)
        self.play(FadeIn(mol), FadeIn(collider), run_time=1.5)
        self.play(mol.animate.move_to(ORIGIN), collider.animate.move_to(ORIGIN), run_time=3)
        
        energy = MathTex(r"E_c > E_a \implies O_2 \to O + O \quad \text{(Dissociation)}").scale(0.85).to_edge(DOWN)
        self.play(Write(energy, run_time=2))
        
        o1 = Dot(radius=0.2, color=RED).move_to([1, 1, 0])
        o2 = Dot(radius=0.2, color=RED).move_to([-1, -1, 0])
        self.play(FadeOut(mol), FadeIn(o1), FadeIn(o2), collider.animate.move_to(RIGHT*4), run_time=3)
        self.wait(2)
        
        # Clean up Part 1
        self.play(FadeOut(o1), FadeOut(o2), FadeOut(collider), FadeOut(energy), FadeOut(desc_tce))
        
        # --- Part 2: Surface Catalysis Recombination ---
        desc_cat = Text("2. Surface Catalysis (TPS Recombination Heating)", font_size=24, color=BLUE_A).to_edge(UP).shift(DOWN*0.9)
        self.play(Write(desc_cat, run_time=2))
        
        wall = Line([3, -2, 0], [3, 2, 0], color=GRAY, stroke_width=4)
        wall_lbl = Text("FTPS Boundary", font_size=18, color=GRAY).next_to(wall, UP)
        self.play(Create(wall), Write(wall_lbl), run_time=1.5)
        
        atom1 = Dot(radius=0.15, color=RED).move_to([-3, 0.5, 0])
        atom2 = Dot(radius=0.15, color=RED).move_to([-3, -0.5, 0])
        self.play(FadeIn(atom1), FadeIn(atom2), run_time=1)
        
        # Move to wall and recombine
        self.play(atom1.animate.move_to([3, 0.3, 0]), atom2.animate.move_to([3, -0.3, 0]), run_time=3)
        
        glowing_wall = Line([3, -1, 0], [3, 1, 0], color=RED, stroke_width=8)
        cat_eq = MathTex(r"O + O \xrightarrow{\text{Surface Catalysis}} O_2 + Q_{\text{recomb}}").scale(0.85).to_edge(DOWN)
        
        self.play(FadeIn(glowing_wall), Write(cat_eq), run_time=1.5)
        
        # Reflect as paired blue diatomic molecule
        recomb_mol = VGroup(Dot(radius=0.15, color=BLUE), Dot(radius=0.15, color=BLUE)).arrange(RIGHT, buff=0.08).move_to([3, 0, 0])
        self.play(FadeOut(atom1), FadeOut(atom2), FadeIn(recomb_mol), run_time=1)
        self.play(recomb_mol.animate.move_to([-3, 0, 0]), glowing_wall.animate.set_color(ORANGE), run_time=3)
        self.wait(2)
        
        # Clean up Part 2
        self.play(FadeOut(wall), FadeOut(wall_lbl), FadeOut(glowing_wall), FadeOut(cat_eq), FadeOut(recomb_mol), FadeOut(desc_cat))
        
        # --- Part 3: Ionization & Radio Blackout ---
        desc_ion = Text("3. High-Speed Ionization & Radio Blackout", font_size=24, color=BLUE_A).to_edge(UP).shift(DOWN*0.9)
        self.play(Write(desc_ion, run_time=2))
        
        atom_n = Dot(radius=0.18, color=WHITE).move_to([-4, 0, 0])
        atom_coll = Dot(radius=0.1, color=GRAY).move_to([0, -0.5, 0])
        self.play(FadeIn(atom_n), FadeIn(atom_coll), run_time=1)
        
        # Ionize at center
        self.play(atom_n.animate.move_to(ORIGIN), atom_coll.animate.move_to(ORIGIN), run_time=2.5)
        
        ion_eq = MathTex(r"N + \text{coll} \xrightarrow{\text{Ionization}} N^+ + e^-").scale(0.85).to_edge(DOWN)
        n_ion = Dot(radius=0.2, color=TEAL).move_to(ORIGIN)
        electron = Dot(radius=0.06, color=YELLOW).move_to(ORIGIN)
        
        self.play(FadeOut(atom_n), FadeOut(atom_coll), FadeIn(n_ion), FadeIn(electron), Write(ion_eq), run_time=1.5)
        
        # Electron flies away extremely fast, Ion moves slowly
        self.play(electron.animate.move_to([4, 2, 0]), n_ion.animate.move_to([1, -1, 0]), run_time=2.5)
        
        # Create a sheath of electrons (multiple small yellow dots)
        sheath = VGroup(*[Dot(radius=0.06, color=YELLOW).move_to([np.random.uniform(2, 4), np.random.uniform(-2, 2), 0]) for _ in range(30)])
        blackout_lbl = Text("Radio Blackout due to Electron Sheath", font_size=20, color=ORANGE).shift(UP*1.5)
        self.play(FadeIn(sheath), Write(blackout_lbl), run_time=1.5)
        
        # Radio wave bouncing off
        radio_wave = FunctionGraph(lambda x: 0.5 * np.sin(4*x), x_range=[-6, 2], color=ORANGE).shift(UP*0.5)
        bounced_wave = FunctionGraph(lambda x: 0.5 * np.sin(-4*x), x_range=[2, 6], color=RED).shift(UP*0.5).rotate(PI/4)
        
        self.play(Create(radio_wave), run_time=3)
        self.play(Transform(radio_wave, bounced_wave), run_time=2)
        self.wait(3)
        
        # Clean up Part 3
        self.play(FadeOut(n_ion), FadeOut(electron), FadeOut(sheath), FadeOut(blackout_lbl), FadeOut(radio_wave), FadeOut(ion_eq), FadeOut(desc_ion))
        
        # --- Part 4: Vacuum Ultraviolet (VUV) Radiative Transport ---
        desc_vuv = Text("4. Vacuum Ultraviolet (VUV) Radiative Aftbody Heating", font_size=24, color=BLUE_A).to_edge(UP).shift(DOWN*0.9)
        self.play(Write(desc_vuv), run_time=2)
        
        # Hot shock layer atoms on the left
        shock_atoms = VGroup(*[Dot(radius=0.15, color=RED).move_to([np.random.uniform(-4, -2), np.random.uniform(-1.5, 1.5), 0]) for _ in range(12)])
        shock_atoms.add(*[Dot(radius=0.15, color=ORANGE).move_to([np.random.uniform(-4, -2), np.random.uniform(-1.5, 1.5), 0]) for _ in range(8)])
        
        # Backshell FTPS wall on the right
        backshell_wall = Line([3, -2, 0], [3, 2, 0], color=GRAY, stroke_width=4)
        backshell_lbl = Text("Aftbody Backshell FTPS", font_size=16, color=GRAY).next_to(backshell_wall, UP)
        
        self.play(FadeIn(shock_atoms), Create(backshell_wall), Write(backshell_lbl), run_time=2)
        
        # VUV radiation rays propagating to the right
        vuv_rays = VGroup()
        for satom in shock_atoms:
            start_pt = satom.get_center()
            vuv_rays.add(Line(start_pt, [3, start_pt[1] + np.random.uniform(-0.5, 0.5), 0], color=YELLOW, stroke_width=1, stroke_opacity=0.6))
        
        # Mathematical equation overlay
        vuv_eq = MathTex(r"\dot{q}_{VUV} \propto \sum h\nu \quad \text{emitted by atomic } N \text{ and } O \quad \text{(Johnston, 2025)}").scale(0.8).to_edge(DOWN)
        
        self.play(Create(vuv_rays), Write(vuv_eq), run_time=3.5)
        
        # Backshell wall begins to glow red as it absorbs VUV radiation
        glowing_backshell = Line([3, -1.8, 0], [3, 1.8, 0], color=RED, stroke_width=8)
        self.play(FadeIn(glowing_backshell), run_time=1.5)
        self.wait(4)
        
        # Clean up Part 4 & Section
        self.play(
            FadeOut(shock_atoms), FadeOut(backshell_wall), FadeOut(backshell_lbl),
            FadeOut(vuv_rays), FadeOut(vuv_eq), FadeOut(glowing_backshell),
            FadeOut(desc_vuv), FadeOut(section_title)
        )

    def post_processing(self):
        section_title = Title("4. Post-Processing: Engineering Metrics")
        self.add(section_title)
        
        # Equations
        eqs = VGroup(
            MathTex(r"Q_{total} = \sum |ke| \quad \text{where } ke \text{ is Column 4 (Kinetic Energy Flux)}"),
            MathTex(r"F_{drag} = \sum |fx| \quad \text{where } fx \text{ is Column 5 (Axial Force)}"),
            MathTex(r"\beta = \frac{m \cdot q}{F_{drag}} \quad \text{(Ballistic Coeff)}"),
            MathTex(r"n = \frac{F_{drag}}{m \cdot g_0} \quad \text{(Deceleration / G-Load)}"),
            MathTex(r"Kn = \frac{\lambda}{D} \quad \text{(Knudsen Number)}"),
            MathTex(r"T_{surf} = \left( \frac{\dot{q}}{\sigma \epsilon} \right)^{0.25} \quad \text{(Radiative Surface Temp)}")
        ).arrange(DOWN, aligned_edge=LEFT).scale(0.8).shift(LEFT*3.2)
        
        self.play(Write(eqs, run_time=8))
        
        # Graph placeholder
        axes = Axes(x_range=[0, 10], y_range=[0, 100], axis_config={"include_tip": False})
        graph = axes.plot(lambda x: 80 * np.exp(-0.5*x), color=BLUE)
        labels = axes.get_axis_labels(x_label="Time", y_label="Metric")
        
        graph_v = VGroup(axes, graph, labels).scale(0.6).shift(RIGHT*4)
        self.play(Create(axes, run_time=4), Write(labels, run_time=3))
        self.play(Create(graph, run_time=5))
        self.wait(10)
        
        self.play(FadeOut(eqs), FadeOut(graph_v), FadeOut(section_title))

    def pinn_refinement(self):
        section_title = Title("5. DeepXDE PINN Refinement (GPU Acceleration)")
        self.add(section_title)
        
        # Explain PINN Concept
        desc = Text("Physics-Informed Neural Network constraints on the flow field [Lu et al., 2021]", font_size=20, color=GRAY).to_edge(UP).shift(DOWN*0.95)
        self.play(Write(desc, run_time=3))
        
        # Loss formula on the right
        loss = MathTex(
            r"\mathcal{L}_{total} = \mathcal{L}_{PDE} + w_{data} \mathcal{L}_{data}"
        ).scale(0.95).shift(RIGHT*3.2 + UP*1.2)
        
        self.play(Write(loss, run_time=4))
        
        # 2D steady compressible Euler equations on the right
        pde_title = Text("2D Steady Compressible Euler Equations:", font_size=16, color=BLUE).shift(RIGHT*3.2 + UP*0.2)
        self.play(FadeIn(pde_title, run_time=2))
        
        pdes = VGroup(
            MathTex(r"R_{cont} = \frac{\partial (\rho u)}{\partial x} + \frac{\partial (\rho v)}{\partial y} + \frac{\rho v}{y} = 0"),
            MathTex(r"R_{mom,x} = \rho \left( u \frac{\partial u}{\partial x} + v \frac{\partial u}{\partial y} \right) + \frac{\partial p}{\partial x} = 0"),
            MathTex(r"R_{mom,y} = \rho \left( u \frac{\partial v}{\partial x} + v \frac{\partial v}{\partial y} \right) + \frac{\partial p}{\partial y} = 0"),
            MathTex(r"R_{EOS} = p - \rho R T = 0")
        ).arrange(DOWN, aligned_edge=LEFT).scale(0.65).next_to(pde_title, DOWN, buff=0.2).align_to(pde_title, LEFT)
        
        self.play(Create(pdes, run_time=8))
        self.wait(5)
        
        # Network visual representation on the left (vertically centered)
        inputs = VGroup(*[Circle(radius=0.15, color=BLUE, fill_opacity=0.8) for _ in range(2)]).arrange(DOWN, buff=0.3).shift(LEFT*5.5 + DOWN*0.5)
        h1 = VGroup(*[Circle(radius=0.15, color=GRAY, fill_opacity=0.5) for _ in range(4)]).arrange(DOWN, buff=0.2).shift(LEFT*3.8 + DOWN*0.5)
        h2 = VGroup(*[Circle(radius=0.15, color=GRAY, fill_opacity=0.5) for _ in range(4)]).arrange(DOWN, buff=0.2).shift(LEFT*2.1 + DOWN*0.5)
        outputs = VGroup(*[Circle(radius=0.15, color=ORANGE, fill_opacity=0.8) for _ in range(5)]).arrange(DOWN, buff=0.15).shift(LEFT*0.4 + DOWN*0.5)
        
        in_labels = VGroup(Text("x", font_size=16), Text("y", font_size=16))
        for idx, lbl in enumerate(in_labels): lbl.next_to(inputs[idx], LEFT, buff=0.1)
        
        out_labels = VGroup(
            MathTex(r"\rho"), MathTex(r"u"), MathTex(r"v"), MathTex(r"T"), MathTex(r"p")
        )
        for idx, lbl in enumerate(out_labels): lbl.scale(0.65).next_to(outputs[idx], RIGHT, buff=0.1)
        
        net = VGroup(inputs, h1, h2, outputs, in_labels, out_labels)
        self.play(FadeIn(net, run_time=4))
        
        # Draw connections
        connections = VGroup()
        for i_n in inputs:
            for h_n in h1:
                connections.add(Line(i_n.get_center(), h_n.get_center(), stroke_width=0.5, color=BLUE, stroke_opacity=0.4))
        for h1_n in h1:
            for h2_n in h2:
                connections.add(Line(h1_n.get_center(), h2_n.get_center(), stroke_width=0.5, color=GRAY, stroke_opacity=0.4))
        for h2_n in h2:
            for o_n in outputs:
                connections.add(Line(h2_n.get_center(), o_n.get_center(), stroke_width=0.5, color=ORANGE, stroke_opacity=0.4))
                
        self.play(Create(connections, run_time=4))
        self.wait(5)
        
        self.play(
            FadeOut(section_title), FadeOut(desc), FadeOut(loss), 
            FadeOut(pde_title), FadeOut(pdes), FadeOut(net), FadeOut(connections)
        )

    def survivability_optimization(self):
        section_title = Title("6. Survivability Optimization and MoP Steering")
        self.add(section_title)
        
        # Describe the closed loop
        desc = Text("Multi-Objective Genetic Algorithm steered by PyTorch Metamodel (MoP)", font_size=20, color=GRAY).to_edge(UP).shift(DOWN*0.95)
        self.play(Write(desc, run_time=3))
        
        # Build formulas
        lhs = MathTex(
            r"x_{i,j} = \min(x_j) + \text{range}(x_j) \cdot \frac{i + r}{N} \quad \text{[McKay et al., 1979]}"
        ).scale(0.75)
        
        cost = MathTex(
            r"J = w_{\beta} \left( \frac{\beta_{calc} - \beta_{target}}{10} \right)^2 + w_{target} \left( \frac{y_{pred} - y_{target}}{1} \right)^2"
        ).scale(0.7)
        
        cost_lbl = Tex("Fitness Cost Function (Natural Selection)", color=YELLOW).scale(0.7)
        
        thermal_p = MathTex(
            r"T_{back} = T_{init} + \frac{\dot{q} \cdot \Delta t \cdot \eta_{lag}}{\rho_{TPS} \cdot C_{p,TPS} \cdot \delta_{TPS}} \le 350\,\text{K} \quad \text{[Johnston, 2025]}"
        ).scale(0.65)
        
        thermal_lbl = Tex("1D Transient TPS Thermal Safety Constraint", color=RED).scale(0.7)
        
        # Group them vertically and shift down slightly
        content_group = VGroup(lhs, cost, cost_lbl, thermal_p, thermal_lbl).arrange(DOWN, buff=0.35)
        content_group.shift(DOWN * 0.55)
        
        # Animate the group elements sequentially
        self.play(Write(lhs, run_time=4))
        self.play(Write(cost, run_time=4))
        self.play(FadeIn(cost_lbl, run_time=2))
        self.wait(5)
        self.play(Write(thermal_p, run_time=4))
        self.play(FadeIn(thermal_lbl, run_time=2))
        self.wait(10)
        
        self.play(
            FadeOut(section_title), FadeOut(desc), FadeOut(content_group)
        )

    def outro(self):
        if hasattr(self, "overlay"):
            self.play(FadeOut(self.overlay), run_time=2)
        final = Text("StellarOrion: Validated Reentry Design", color=BLUE_D)
        self.play(Write(final, run_time=5))
        self.wait(10)
        self.play(FadeOut(final))

if __name__ == "__main__":
    pass
