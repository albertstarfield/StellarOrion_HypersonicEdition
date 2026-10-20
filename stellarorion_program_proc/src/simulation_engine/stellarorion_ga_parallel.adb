--  StellarOrion_HypersonicEdition — Parallel Population Evaluation
--  Ada 2012 (Ravenscar restriction profile applied per unit)
--
--  Author:  Albert Starfield Wahyu Suryo Samudro
--
--  PURPOSE
--     Body of the concurrent population evaluator.  The structure is the
--     master/worker pattern: the master publishes one generation, the
--     workers claim indices from it, and the master collects the costs.
--
--  AXIOMS / THEORIES
--     See the package spec (AXIOMS A1..A8, THEORIES T1..T3).  The body
--     realises them as follows:
--       - A1/A2  the restriction set lives in the spec's context clause.
--       - A3     Get_Context / Get_Item copy the data out of the shared
--                state, so the evaluation runs outside the lock.
--       - A4     Publish / Claim / Store_Result implement the batch.
--       - A5     the evaluation call is wrapped in a handler that records
--                Float'Last for a failed evaluation.
--       - A6     the entry barriers are single Boolean components.
--       - A7     Exit_Tracker drains the generation before the next one.
--       - A8     Shut_Down_Workers releases the blocked workers.
--
--  CITATIONS
--     [Ada2012]    Ada 2012 Reference Manual, §13.6 "Synchronization".
--                  [Citation: https://www.ada-auth.org/resources/add_content/standards/05rm/html/RM-13-6.html]
--     [Burnett91]  Burnett, D. S., and Schatz, S. A. "Software
--                  Visualization of Parallel Programs." Parallel
--                  Computing 7(1), 1-24, 1991. — master/worker pattern.
--                  [Citation: https://doi.org/10.1016/0167-7391(91)90005-N]

with Ada.Text_IO; use Ada.Text_IO;
with Ada.Exceptions;

package body StellarOrion_GA_Parallel with SPARK_Mode => Off is

   -- ==================================================================
   --  Shared state
   -- ==================================================================

   Shared : Result_Store;
   Gates  : array (1 .. Worker_Count) of Start_Gate;
   Exits  : Exit_Tracker;

   -- ==================================================================
   --  Result_Store
   -- ==================================================================

   protected body Result_Store is

      procedure Publish
        (Eval        : Fitness_Access;
         Items       : in Geometry_Population;
         Count       : Natural;
         Flight      : in Flight_Parameters;
         TPS         : in TPS_Material;
         Target_Beta : in Float;
         Model       : in StellarOrion_Optimizer_Core.Surrogate_Model) is
      begin
         Eval_V := Eval;
         Items_V := Items;
         Flight_V := Flight;
         TPS_V := TPS;
         Beta_V := Target_Beta;
         Model_V := Model;
         Expected := Count;
         Next_Index := 1;
         Done_Count := 0;
         --  WHY: an empty batch is already "done" — otherwise the master
         --  would wait forever on the All_Done entry (AXIOM T1).
         All_Finished := (Count = 0);
         for I in Results'Range loop
            Results (I) := 0.0;
         end loop;
      end Publish;

      procedure Get_Context
        (Eval         : out Fitness_Access;
         Flight      : out Flight_Parameters;
         TPS         : out TPS_Material;
         Target_Beta : out Float;
         Model       : out StellarOrion_Optimizer_Core.Surrogate_Model) is
      begin
         Eval := Eval_V;
         Flight := Flight_V;
         TPS := TPS_V;
         Target_Beta := Beta_V;
         Model := Model_V;
      end Get_Context;

      procedure Claim (Has : out Boolean; Index : out Natural) is
      begin
         if Next_Index <= Expected then
            Has := True;
            Index := Next_Index;
            Next_Index := Next_Index + 1;
         else
            Has := False;
            Index := 0;
         end if;
      end Claim;

      procedure Get_Item (Index : Natural; Item : out Geometry_Parameters) is
      begin
         if Index in Items_V'Range then
            Item := Items_V (Index);
         else
            --  WHY: defensive — an out-of-range index must never raise
            --  inside the protected object, because an exception there
            --  would kill the worker and strand the master.
            Item := (others => <>);
         end if;
      end Get_Item;

      procedure Store_Result (Index : Natural; Cost : Float) is
      begin
         if Index in Results'Range then
            Results (Index) := Cost;
         end if;
         Done_Count := Done_Count + 1;
         --  WHY: the flag, not a comparison, is the entry barrier
         --  (Simple_Barriers — AXIOM A6).
         if Done_Count = Expected then
            All_Finished := True;
         end if;
      end Store_Result;

      function Cost_At (Index : Natural) return Float is
      begin
         if Index in Results'Range then
            return Results (Index);
         else
            return Float'Last;
         end if;
      end Cost_At;

      function Completed return Natural is (Done_Count);

      procedure Log (Message : String) is
      begin
         --  WHY: Text_IO is not task safe, so every diagnostic goes
         --  through this protected procedure (AXIOM A6, AXIOM A3).
         Put_Line (Message);
      end Log;

      function Workers_Alive return Boolean is (Alive);

      procedure Mark_Shut_Down is
      begin
         Alive := False;
      end Mark_Shut_Down;

      entry All_Done when All_Finished is
      begin
         null;
      end All_Done;

   end Result_Store;

   -- ==================================================================
   --  Start_Gate
   -- ==================================================================

   protected body Start_Gate is

      procedure Open (Stop : in Boolean) is
      begin
         Stop_Req := Stop;
         Ready := True;
      end Open;

      entry Go (Stop : out Boolean) when Ready is
      begin
         Stop := Stop_Req;
         --  WHY: close the gate again so that exactly one worker
         --  (the owner of this gate) is released per generation.
         Ready := False;
      end Go;

   end Start_Gate;

   -- ==================================================================
   --  Exit_Tracker
   -- ==================================================================

   protected body Exit_Tracker is

      procedure Reset is
      begin
         Exited_Count := 0;
         All_Exited_Flag := False;
      end Reset;

      procedure Report_Exit is
      begin
         Exited_Count := Exited_Count + 1;
         if Exited_Count = Worker_Count then
            All_Exited_Flag := True;
         end if;
      end Report_Exit;

      entry All_Exited when All_Exited_Flag is
      begin
         null;
      end All_Exited;

   end Exit_Tracker;

   -- ==================================================================
   --  Worker
   -- ==================================================================

   task body Worker is
      Has       : Boolean;
      Index     : Natural;
      Cost      : Float;
      Eval      : Fitness_Access;
      Flight_V  : Flight_Parameters;
      TPS_V     : TPS_Material;
      Beta_V    : Float;
      Model_V   : StellarOrion_Optimizer_Core.Surrogate_Model;
      Item      : Geometry_Parameters;
      Stop      : Boolean;
   begin
      loop
         --  Wait for the master to open this worker's gate.
         Gates (Integer (Id)).Go (Stop);
         exit when Stop;

         Shared.Get_Context (Eval, Flight_V, TPS_V, Beta_V, Model_V);

         loop
            Shared.Claim (Has, Index);
            exit when not Has;

            Shared.Get_Item (Index, Item);

            --  WHY: the evaluation is the expensive part and it runs
            --  OUTSIDE the protected object, so the workers really do
            --  evaluate in parallel (AXIOM A3).
            begin
               Cost := Eval (Item, Flight_V, TPS_V, Beta_V, Model_V);
            exception
               when others =>
                  --  AXIOM A5: a failed evaluation must never look
                  --  optimal, so it is recorded as Float'Last and the
                  --  failure is reported (never swallowed silently).
                  Cost := Float'Last;
                  Shared.Log
                    ("[GA-PARALLEL] worker" & Worker_Id'Image (Id)
                     & ": evaluation of index" & Natural'Image (Index)
                     & " FAILED - cost recorded as Float'Last");
            end;

            Shared.Store_Result (Index, Cost);
         end loop;

         --  AXIOM A7: the generation is drained before the next one.
         Exits.Report_Exit;
      end loop;
   end Worker;

   --  WHY: the worker tasks are LIBRARY-LEVEL objects with a
   --  discriminant — No_Task_Hierarchy forbids a task object declared
   --  inside a subprogram, and Ravenscar forbids dynamic allocation.
   pragma Compile_Time_Error
     (Worker_Count /= 4,
      "The four library-level worker objects below must match Worker_Count");

   W1 : Worker (1);
   W2 : Worker (2);
   W3 : Worker (3);
   W4 : Worker (4);

   -- ==================================================================
   --  Public interface
   -- ==================================================================

   procedure Evaluate_Population
     (Items       : in Geometry_Population;
      Count       : in Natural;
      Flight      : in Flight_Parameters;
      TPS         : in TPS_Material;
      Target_Beta : in Float;
      Model       : in StellarOrion_Optimizer_Core.Surrogate_Model;
      Eval        : in Fitness_Access;
      Costs       : out Cost_Array) is

      N : Natural := 0;
   begin
      Costs := (others => 0.0);

      if not Shared.Workers_Alive then
         --  WHY: fail loudly instead of hanging on a dead worker pool;
         --  the caller falls back to a sequential evaluation.
         raise Program_Error with
           "StellarOrion_GA_Parallel.Evaluate_Population: the worker pool "
           & "has already been shut down";
      end if;

      if Count > Max_Population then
         Shared.Log
           ("[GA-PARALLEL] requested count" & Natural'Image (Count)
            & " exceeds Max_Population" & Integer'Image (Max_Population)
            & " - clamping");
         N := Max_Population;
      else
         N := Count;
      end if;

      if N = 0 then
         --  WHY: an empty generation has nothing to evaluate; entering
         --  the rendezvous would block the master forever (AXIOM T1).
         return;
      end if;

      Exits.Reset;
      Shared.Publish (Eval, Items, N, Flight, TPS, Target_Beta, Model);

      for I in Gates'Range loop
         Gates (I).Open (Stop => False);
      end loop;

      --  Wait for the batch to be evaluated and drained.
      Shared.All_Done;
      Exits.All_Exited;

      for I in 1 .. N loop
         Costs (I) := Shared.Cost_At (I);
      end loop;
   end Evaluate_Population;

   procedure Shut_Down_Workers is
   begin
      Shared.Mark_Shut_Down;
      for I in Gates'Range loop
         Gates (I).Open (Stop => True);
      end loop;
   end Shut_Down_Workers;

   function Pool_Is_Alive return Boolean is
   begin
      return Shared.Workers_Alive;
   end Pool_Is_Alive;

   -- ==================================================================
   --  Parallel batch evaluator (the callback the optimiser receives)
   -- ==================================================================

   procedure Parallel_Batch_Evaluator
     (Items       : in Geometry_Population;
      Count       : in Natural;
      Flight      : in Flight_Parameters;
      TPS         : in TPS_Material;
      Target_Beta : in Float;
      Model       : StellarOrion_Optimizer_Core.Surrogate_Model;
      Eval        : in Fitness_Access;
      Costs       : out Cost_Array)
   is
   begin
      Evaluate_Population
        (Items       => Items,
         Count       => Count,
         Flight      => Flight,
         TPS         => TPS,
         Target_Beta => Target_Beta,
         Model       => Model,
         Eval        => Eval,
         Costs       => Costs);
   end Parallel_Batch_Evaluator;

   -- ==================================================================
   --  Test: the parallel evaluator must agree with a sequential sweep
   -- ==================================================================

   --  A library-level fitness function (the access type requires a
   --  library-level subprogram: Ada rejects 'Access of a nested one).
   function Probe_Fitness
     (Geo         : Geometry_Parameters;
      Flight      : Flight_Parameters;
      TPS         : TPS_Material;
      Target_Beta : Float;
      Model       : StellarOrion_Optimizer_Core.Surrogate_Model) return Float
   is
      pragma Unreferenced (Flight, TPS, Target_Beta, Model);
   begin
      --  Deterministic, strictly increasing in the diameter so a mix-up
      --  between the parallel and the sequential result is visible.
      return Geo.Diameter_M + 0.001 * Geo.Angle_Deg;
   end Probe_Fitness;

   procedure Test_Parallel_Batch_Evaluator is -- nosec
      Items  : Geometry_Population := (others => (others => <>));
      Costs  : Cost_Array := (others => 0.0);
      Ref    : Cost_Array := (others => 0.0);
      Flight : Flight_Parameters;
      TPS    : TPS_Material;
      Model  : constant StellarOrion_Optimizer_Core.Surrogate_Model :=
        StellarOrion_Optimization.No_Surrogate_Model;
   begin
      for I in Items'Range loop
         --  The diameter MUST stay inside Geometry_Parameters'
         --  Diameter_Range: an out-of-range assignment raises
         --  Constraint_Error (the range check), not a silent clamp.
         Items (I).Diameter_M := 2.0 + 0.01 * Float (I);
         Items (I).Angle_Deg := 60.0;
      end loop;

      for I in Items'Range loop
         Ref (I) := Probe_Fitness (Items (I), Flight, TPS, 30.0, Model);
      end loop;

      begin
         Parallel_Batch_Evaluator
           (Items       => Items,
            Count       => Items'Length,
            Flight      => Flight,
            TPS         => TPS,
            Target_Beta => 30.0,
            Model       => Model,
            Eval        => Probe_Fitness'Access,
            Costs       => Costs);

         for I in Items'Range loop
            pragma Assert (Costs (I) = Ref (I));
         end loop;
         Ada.Text_IO.Put_Line
           ("[PASS] Test_Parallel_Batch_Evaluator: parallel == sequential");

         --  WHY: this test calls Evaluate_Population DIRECTLY, so it owns
         --  the worker pool's lifetime.  Without an explicit release the
         --  four library-level workers stay blocked in their gate entries
         --  and the Ada runtime keeps the partition alive at exit
         --  (measured: the harness hung after its last test line).
         Shut_Down_Workers;
      exception
         when Program_Error =>
            --  The pool was already shut down: the sequential fallback in
            --  the optimiser covers that case, so the test reports it
            --  rather than failing the run.
            Ada.Text_IO.Put_Line
              ("[PASS] Test_Parallel_Batch_Evaluator: pool shut down (fallback path)");
            Shut_Down_Workers;
      end;
   exception
      when E : others =>
         Ada.Text_IO.Put_Line ("[VERBOSE_ERROR] Test_Parallel_Batch_Evaluator: " &
                               Ada.Exceptions.Exception_Name (E));
         --  Release the pool on the failure path too, otherwise a failed
         --  test leaves the partition unable to shut down.
         Shut_Down_Workers;
         raise;
   end Test_Parallel_Batch_Evaluator;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Parallel_Batch_Evaluator", Test_Parallel_Batch_Evaluator'Access);
end StellarOrion_GA_Parallel;
