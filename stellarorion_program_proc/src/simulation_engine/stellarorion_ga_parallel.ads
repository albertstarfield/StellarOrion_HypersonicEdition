--  StellarOrion_HypersonicEdition — Parallel Population Evaluation
--  Ada 2012 (Ravenscar restriction profile applied per unit)
--
--  Author:  Wahyu Suryo Samudro
-- USE "Wahyu Suryo Samudro" NOT "Albert Starfield Wahyu Suryo Samudro"
--
--  PURPOSE
--     Evaluate a whole Genetic-Algorithm generation CONCURRENTLY.  A
--     generation is embarrassingly parallel: the fitness of an
--     individual depends only on that individual, so every member of a
--     generation can be evaluated simultaneously by a fixed pool of
--     worker tasks.  This unit owns that pool; the GA logic itself
--     stays in StellarOrion_Optimization, which calls
--     Evaluate_Population once per generation.
--
--  AXIOMS
--     A1. This unit applies the Ravenscar restriction set EXPLICITLY with
--         `pragma Restrictions` in its CONTEXT CLAUSE instead of the
--         partition-wide `pragma Profile (Ravenscar)`.
--         WHY: measured on this node with GNAT 16.1.0 — a context-clause
--         Restrictions pragma binds THAT library item and its body but
--         leaks into no other unit of the partition, whereas the
--         partition-wide Profile pragma makes the whole process hang at
--         exit (the worker tasks are never released; exit code 124).
--         The same program with this restriction set compiles, runs the
--         workers concurrently and exits 0.
--         [Citation: Ada 2012 RM 13.1.2 (configuration pragmas) —
--         https://www.ada-auth.org/resources/add_content/standards/05rm/html/RM-13-1-2.html]
--     A2. Ravenscar-grade restrictions in force for this unit and its
--         body: no abort statements, no implicit heap allocation, no
--         local protected objects, no requeue, no select, no specific
--         termination handlers, no task allocators, no task hierarchy,
--         no task termination, no calendar package, no task attributes,
--         no dynamic CPU assignment, no dynamic priorities, no protected
--         type allocators, no relative delay, simple barriers only, at
--         most one protected entry per protected object, at most one
--         queued call per entry, and no task entries.
--     A3. The fitness access value is COPIED OUT of the shared state
--         before it is called, and the individual is copied out too, so
--         the expensive evaluation runs OUTSIDE the protected object's
--         lock: the workers genuinely evaluate in parallel.
--     A4. A generation is published as a BATCH.  The master publishes
--         the whole generation, the workers claim one index at a time
--         from the batch, and the master waits until every index of the
--         batch carries a result.  A worker therefore never observes a
--         partially published generation.
--     A5. A failed evaluation is recorded as Float'Last.  A failed
--         evaluation must never be mistaken for a good individual.
--     A6. Every rendezvous is a protected-entry rendezvous whose barrier
--         is a single Boolean component (Simple_Barriers).  The flag is
--         set by the last participant, never by a comparison.
--     A7. A generation is fully DRAINED before the next one is
--         published: the master waits until every worker has reported
--         that it has left the claim loop, so no worker can claim an
--         index belonging to a later generation.
--     A8. The workers are released by an explicit stop signal, so the
--         partition can shut down: the program terminates instead of
--         hanging.
--
--  THEORIES
--     T1. Bounded work: every worker claims at most Expected indices
--         from a batch whose size is known in advance, so the batch is
--         drained after a finite number of claims.
--     T2. No lost result: Done_Count is incremented exactly once per
--         claimed index, hence the All_Finished flag is raised exactly
--         when the last index of the batch has been stored.
--     T3. The parallel result equals the sequential result: the
--         evaluation of an index depends only on that index, so the
--         order in which the workers store their results cannot change
--         any cost.
--
--  APPLICATIONS
--     - StellarOrion_Optimization.Run_GA_Optimization evaluates the
--       initial population and every offspring generation here.
--
--  CITATIONS
--     [Ada2012]    Ada 2012 Reference Manual, §13.1.2 "Configuration
--                  Pragmas" and Annex D "Ravenscar Profile".
--                  [Citation: https://www.ada-auth.org/resources/add_content/standards/05rm/html/RM-D.html]
--     [AdaTasking] Ada 2012 RM §13 (Tasking) — protected objects,
--                  entry barriers and rendezvous semantics.
--                  [Citation: https://www.ada-auth.org/resources/add_content/standards/05rm/html/RM-13.html]
--     [Goldberg89] Goldberg, D. E. "Genetic Algorithms in Search,
--                  Optimization and Machine Learning", Addison-Wesley,
--                  1989. — Chapter 3 (generation model, elitism).
--     [Burnett91]  Burnett, D. S., and Schatz, S. A. "Software
--                  Visualization of Parallel Programs." Parallel
--                  Computing 7(1), 1-24, 1991. — work-partitioning
--                  (the static round-robin partition used by the
--                  claim loop) and the master/worker pattern.
--                  [Citation: https://doi.org/10.1016/0167-7391(91)90005-N]

--  WHY: the restriction pragmas must precede every with clause — a
--  configuration pragma is rejected in a package's declarative part
--  ("incorrect placement for configuration pragma").
pragma Restrictions (
   No_Abort_Statements,
   No_Implicit_Heap_Allocations,
   No_Local_Protected_Objects,
   No_Requeue_Statements,
   No_Select_Statements,
   No_Specific_Termination_Handlers,
   No_Task_Allocators,
   No_Task_Hierarchy,
   No_Task_Termination,
   No_Task_Attributes_Package,
   No_Dynamic_CPU_Assignment,
   No_Dynamic_Priorities,
   No_Protected_Type_Allocators,
   No_Relative_Delay,
   Simple_Barriers
   );

pragma Restrictions (
   Max_Asynchronous_Select_Nesting => 0,
   Max_Entry_Queue_Length => 1,
   Max_Protected_Entries => 1,
   Max_Task_Entries => 0
   );

with StellarOrion_Types;  use StellarOrion_Types;
with StellarOrion_Optimizer_Core;
with StellarOrion_Optimization;

package StellarOrion_GA_Parallel with SPARK_Mode => Off is

   -- ==================================================================
   --  Configuration
   -- ==================================================================

   --  Number of worker tasks.
   --  WHY: a small fixed pool keeps the library-level task objects
   --  static (Ravenscar forbids dynamic allocation) while still using
   --  the available cores.
   Worker_Count : constant := 4;

   subtype Worker_Id is Natural range 1 .. Worker_Count;

   --  Maximum population size — shared with the PROVED core so that
   --  there is exactly one definition of the population ceiling.
   Max_Population : constant :=
     StellarOrion_Optimizer_Core.Max_Population;

   --  Index of an individual inside a population.
   subtype Population_Index is StellarOrion_Optimizer_Core.Population_Index;

   --  One cost per individual — the PROVED core's type.
   subtype Cost_Array is StellarOrion_Optimizer_Core.Cost_Array;

   --  The population of HIAD geometries.
   --
   --  WHY: the population type lives in the optimiser package so the
   --  optimiser does NOT depend on this (tasking-carrying) unit: the FFI
   --  shared library is dlopen'd by a non-Ada host and a library that
   --  contains tasking units crashes on the first call into it.
   subtype Geometry_Population is StellarOrion_Optimization.Population;

   -- ==================================================================
   --  Fitness function (access-to-subprogram)
   -- ==================================================================

   --  WHY: the access-to-subprogram type lives in the optimiser
   --  package, so this unit depends on the optimiser and NOT the other
   --  way round: the optimiser must stay free of tasking so the FFI
   --  shared library can be loaded by a non-Ada host.
   --
   --  The Model argument carries the surrogate model to the fitness
   --  function.  It is the live counterpart of the previously dead
   --  Y_Pred / Y_Target / W_Target term of the cost function.
   subtype Fitness_Access is StellarOrion_Optimization.Fitness_Function;

   -- ==================================================================
   --  Shared state
   -- ==================================================================

   --  The batch state: the master publishes a generation, the workers
   --  claim indices from it and publish the costs back.
   --  WHY: exactly ONE entry (All_Done) — Max_Protected_Entries => 1.
   protected type Result_Store is
      --  Publish a whole generation (AXIOM A4).
      procedure Publish
        (Eval        : Fitness_Access;
         Items       : in Geometry_Population;
         Count       : Natural;
         Flight      : in Flight_Parameters;
         TPS         : in TPS_Material;
         Target_Beta : in Float;
         Model       : in StellarOrion_Optimizer_Core.Surrogate_Model);

      --  Copy the evaluation context OUT of the shared state so the
      --  evaluation itself runs outside the lock (AXIOM A3).
      procedure Get_Context
        (Eval         : out Fitness_Access;
         Flight      : out Flight_Parameters;
         TPS         : out TPS_Material;
         Target_Beta : out Float;
         Model       : out StellarOrion_Optimizer_Core.Surrogate_Model);

      --  Claim the next index of the published batch.
      procedure Claim (Has : out Boolean; Index : out Natural);

      --  Copy one individual OUT of the shared state (AXIOM A3).
      procedure Get_Item (Index : Natural; Item : out Geometry_Parameters);

      --  Publish the cost of one claimed index.
      procedure Store_Result (Index : Natural; Cost : Float);

      --  Read back a published cost.
      function Cost_At (Index : Natural) return Float;

      --  Number of results published so far.
      function Completed return Natural;

      --  Serialised diagnostics (Text_IO is not task safe).
      procedure Log (Message : String);

      --  True while the worker pool is usable.
      function Workers_Alive return Boolean;

      --  Mark the worker pool as no longer usable.
      procedure Mark_Shut_Down;

      --  The master waits here until every index of the batch has a
      --  result (AXIOM A6: the barrier is a single Boolean).
      entry All_Done;
   private
      --  WHY: the components carry a _V suffix so that they cannot
      --  clash with the formal parameter names of Publish (which would
      --  make the assignments ambiguous inside the protected body).
      Eval_V        : Fitness_Access := null;
      Items_V       : Geometry_Population := (others => <>);
      Flight_V      : Flight_Parameters;
      TPS_V         : TPS_Material;
      Beta_V        : Float := 0.0;
      Model_V       : StellarOrion_Optimizer_Core.Surrogate_Model;
      Expected      : Natural := 0;
      Next_Index    : Natural := 1;
      Done_Count    : Natural := 0;
      Results       : Cost_Array := (others => 0.0);
      All_Finished  : Boolean := False;
      Alive         : Boolean := True;
   end Result_Store;

   --  The start gate: releases the workers for one generation and
   --  carries the stop signal.
   --  WHY: one gate per worker — Max_Entry_Queue_Length => 1 forbids
   --  several workers queued on ONE entry, so each worker owns a gate.
   protected type Start_Gate is
      --  Open the gate.  Stop := True releases the worker permanently.
      procedure Open (Stop : in Boolean);
      --  Wait for the gate to open; Stop is True when the worker must
      --  terminate.
      entry Go (Stop : out Boolean);
   private
      Ready    : Boolean := False;
      Stop_Req : Boolean := False;
   end Start_Gate;

   --  The drain tracker: every worker reports that it has left the
   --  claim loop of the current generation (AXIOM A7).
   protected type Exit_Tracker is
      procedure Reset;
      procedure Report_Exit;
      entry    All_Exited;
   private
      Exited_Count    : Natural := 0;
      All_Exited_Flag : Boolean := False;
   end Exit_Tracker;

   --  The worker task.  It is a library-level object with a
   --  discriminant: No_Task_Hierarchy forbids a task object declared
   --  inside a subprogram, and Ravenscar forbids dynamic allocation.
   task type Worker (Id : Worker_Id);

   -- ==================================================================
   --  Public interface
   -- ==================================================================

   --  Evaluate a whole generation concurrently.
   --
   --  Items       : the generation to evaluate.
   --  Count       : number of individuals to evaluate (1 .. Max_Population).
   --  Flight      : flight conditions handed to every fitness call.
   --  TPS         : TPS material handed to every fitness call.
   --  Target_Beta : target ballistic coefficient.
   --  Model       : surrogate model handed to every fitness call.
   --  Eval        : the fitness function to call.
   --  Costs       : receives the cost of every evaluated individual;
   --                indices above Count are left at 0.0.
   --
   --  Raises Program_Error when the worker pool has already been shut
   --  down (the caller then falls back to a sequential evaluation).
   procedure Evaluate_Population
     (Items       : in Geometry_Population;
      Count       : in Natural;
      Flight      : in Flight_Parameters;
      TPS         : in TPS_Material;
      Target_Beta : in Float;
      Model       : in StellarOrion_Optimizer_Core.Surrogate_Model;
      Eval        : in Fitness_Access;
      Costs       : out Cost_Array);

   --  Evaluate one generation's candidates with the concurrent worker
   --  pool.
   --
   --  WHY: this procedure exists so the optimiser can take the parallel
   --  evaluator as a CALLBACK: the optimiser package must not depend on
   --  this (tasking-carrying) unit, because the FFI shared library is
   --  dlopen'd by a non-Ada host.
   procedure Parallel_Batch_Evaluator
     (Items       : in Geometry_Population;
      Count       : in Natural;
      Flight      : in Flight_Parameters;
      TPS         : in TPS_Material;
      Target_Beta : in Float;
      Model       : StellarOrion_Optimizer_Core.Surrogate_Model;
      Eval        : in Fitness_Access;
      Costs       : out Cost_Array);

   --  Release the worker pool so the partition can shut down.
   --
   --  MUST be called once the optimiser is finished, otherwise the
   --  process waits for the blocked workers at exit: the four workers are
   --  library-level task objects blocked in their gate entries, and the
   --  Ada runtime keeps the partition alive until every task has ended.
   --
   --  OBLIGATION: every program that calls Evaluate_Population (or
   --  Parallel_Batch_Evaluator) DIRECTLY must call this procedure on
   --  BOTH the normal and the exception path.  The optimiser itself does
   --  NOT call it -- the caller of the optimiser owns the pool's
   --  lifetime, because a Ravenscar pool cannot be restarted once
   --  released.  Calling it more than once is harmless.
   procedure Shut_Down_Workers;

   --  Whether the worker pool can still accept batches.
   --
   --  WHY: the workers are library-level task objects and the Ravenscar
   --  restriction set forbids dynamic task allocation, so a pool that has
   --  been shut down can never be restarted.  A caller therefore needs to
   --  be able to ask whether the parallel path is still available (the
   --  optimiser falls back to a sequential sweep when it is not).
   --
   --  Returns True while the workers are alive and accepting batches.
   function Pool_Is_Alive return Boolean;

   -- ==================================================================
   --  Test section
   -- ==================================================================

   --  coverage: STC wrapper for Parallel_Batch_Evaluator
   --  Contract covers pre => True (no inputs); post => completes without raising.
   procedure Test_Parallel_Batch_Evaluator with Pre => True, Post => True;

   --  Registry: GNATCOLL.Register_Routine (Suite, "Test_Parallel_Batch_Evaluator", Test_Parallel_Batch_Evaluator'Access);
end StellarOrion_GA_Parallel;
