--  Dump the LHS-seeded initial population of the double pass GA.
--  Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
--
--  WHY THIS EXISTS
--  ---------------
--  The thesis and the deck both claim that the genetic algorithm starts from
--  a Latin hypercube of fifty individuals, but neither the thesis nor the
--  recorded artifact stores those fifty individuals: the artifact keeps only
--  the best design of each generation.  This main reproduces the seeding
--  exactly as the GA engine performs it and prints the whole population, so
--  the claim can be checked against the recorded generation-0 winner instead
--  of being taken on faith.
--
--  AXIOMS
--  ------
--  A1: The GA engine seeds by calling Reset (Gen, Config.Seed) and then
--      running the Fisher-Yates plus LHS_Sample loop of
--      Seed_LHS_Population with no other draw in between, so the
--      population is a pure function of (seed, population size).
--  A2: The analytic triple stored in the artifact is
--      R_N = Diameter_M / 2, r_tor = Toroid_Radius_M,
--      half_cone = Angle_Deg (SBO_Fitness comment, optimization body).
--  A3: stdout of this main is data only; diagnostics go to stderr.
--
--  THEORIES
--  --------
--  T1: Because A1 holds, running the same loop here on a generator reset
--      with the same initiator yields byte-identical genes, and therefore
--      the same best individual under the analytic cost.
--  T2: If the regenerated population's cost minimiser does not equal the
--      artifact's history[0], the reproduction failed and the dump must be
--      rejected rather than plotted.
--
--  APPLICATIONS
--  ------------
--      gprbuild -P stellarorion_program_proc.gpr dump_lhs.adb
--      ./bin/dump_lhs > population.json
--
--  CITATIONS
--  ---------
--  [1] McKay, M.D., Beckman, R.J., Conover, W.J. "Latin Hypercube
--      Sampling," Technometrics 21(2), 1979, Eq. (2.1).
--  [2] Ada 2022 RM A.4.3 - Random Number Generation (Reset, Random).
--  [3] GNAT 16.1.0 System.Random_Numbers (s-rannum.adb), the generator
--      behind Ada.Numerics.Float_Random: period 2**19937-1.

with Ada.Numerics.Float_Random;
with Ada.Text_IO;
with StellarOrion_Optimization;

procedure Dump_LHS is

   Pop_Size : constant := 50;
   Seed     : constant := 42;

   Gen  : Ada.Numerics.Float_Random.Generator;
   Pop  : StellarOrion_Optimization.Population;
   Perm : array (1 .. Pop_Size) of Positive;
   R    : Float;

   package F_IO is new Ada.Text_IO.Float_IO (Float);

   --  Print a float with enough decimals that Python can rebuild the cost
   --  from it without losing the last bits of the binary value.
   procedure Put_F (X : Float) is
   begin
      F_IO.Put (X, Fore => 12, Aft => 15, Exp => 0);
   end Put_F;

begin
   --  A1: the engine's own first act is Reset with the configured seed.
   Ada.Numerics.Float_Random.Reset (Gen, Seed);

   --  The genes the GA does not optimise keep their record defaults, which
   --  is what the seeding procedure does before it samples.
   for I in 1 .. Pop_Size loop
      Pop (I) := (others => <>);
   end loop;

   --  Per gene: a fresh random permutation of the strata, then one
   --  stratified value per individual.  This is the body of
   --  Seed_LHS_Population (StellarOrion_Optimization) transcribed, because
   --  that procedure is private to the package body and cannot be called
   --  from here.  The order of the draws is what makes T1 hold, so the
   --  order below must not be changed.
   for Gene in 1 .. 6 loop
      for I in 1 .. Pop_Size loop
         Perm (I) := I;
      end loop;
      for I in reverse 2 .. Pop_Size loop
         declare
            J : constant Positive :=
              1 + Integer (Ada.Numerics.Float_Random.Random (Gen) * Float (I));
            T : constant Positive := Perm (I);
         begin
            Perm (I) := Perm (J);
            Perm (J) := T;
         end;
      end loop;

      for I in 1 .. Pop_Size loop
         R := Ada.Numerics.Float_Random.Random (Gen);
         case Gene is
            when 1 =>
               Pop (I).Diameter_M :=
                 StellarOrion_Optimization.LHS_Sample
                   (StellarOrion_Optimization.Dia_Min,
                    StellarOrion_Optimization.Dia_Max,
                    Pop_Size, Perm (I), R);
            when 2 =>
               Pop (I).Angle_Deg :=
                 StellarOrion_Optimization.LHS_Sample
                   (StellarOrion_Optimization.Ang_Min,
                    StellarOrion_Optimization.Ang_Max,
                    Pop_Size, Perm (I), R);
            when 3 =>
               Pop (I).Nose_Radius_M :=
                 StellarOrion_Optimization.LHS_Sample
                   (StellarOrion_Optimization.Nos_Min,
                    StellarOrion_Optimization.Nos_Max,
                    Pop_Size, Perm (I), R);
            when 4 =>
               Pop (I).Toroid_Count :=
                 Integer
                   (Float'Floor
                      (StellarOrion_Optimization.LHS_Sample
                         (Float (StellarOrion_Optimization.TCount_Min),
                          Float (StellarOrion_Optimization.TCount_Max),
                          Pop_Size, Perm (I), R)
                       + 0.5));
            when 5 =>
               Pop (I).Toroid_Radius_M :=
                 StellarOrion_Optimization.LHS_Sample
                   (StellarOrion_Optimization.TRad_Min,
                    StellarOrion_Optimization.TRad_Max,
                    Pop_Size, Perm (I), R);
            when others =>
               Pop (I).Mass_Kg :=
                 StellarOrion_Optimization.LHS_Sample
                   (StellarOrion_Optimization.Mass_Min,
                    StellarOrion_Optimization.Mass_Max,
                    Pop_Size, Perm (I), R);
         end case;
      end loop;
   end loop;

   --  One JSON object per line, so a reader can stream the file.
   for I in 1 .. Pop_Size loop
      Ada.Text_IO.Put ("{""i"":" & Integer'Image (I) & ",");
      Ada.Text_IO.Put ("""Diameter_M"":");
      Put_F (Pop (I).Diameter_M);
      Ada.Text_IO.Put (",""Angle_Deg"":");
      Put_F (Pop (I).Angle_Deg);
      Ada.Text_IO.Put (",""Nose_Radius_M"":");
      Put_F (Pop (I).Nose_Radius_M);
      Ada.Text_IO.Put (",""Toroid_Count"":");
      Ada.Text_IO.Put (Integer'Image (Pop (I).Toroid_Count));
      Ada.Text_IO.Put (",""Toroid_Radius_M"":");
      Put_F (Pop (I).Toroid_Radius_M);
      Ada.Text_IO.Put (",""Mass_Kg"":");
      Put_F (Pop (I).Mass_Kg);
      Ada.Text_IO.Put_Line ("}");
   end loop;
end Dump_LHS;
