(* StellarOrion HypersonicEdition — Rocq Formal Proof Skeletons
   ============================================================
   These Coq/Rocq files provide machine-checked proof obligations
   for the core physics functions. They serve as specifications that
   the Ada/SPARK implementation must satisfy.

   Author: Albert Starfield Wahyu Suryo Samudro *)

(* ---- Mean Free Path Properties ---- *)
(* Prove: lambda > 0 when n > 0 and d > 0 *)
(* Prove: lambda decreases monotonically with n *)

Section MeanFreePath.
  Variable n : R.       (* number density [m^-3] *)
  Variable d : R.       (* molecular diameter [m] *)
  Variable sqrt2 : R.   (* sqrt(2) *)
  Variable pi : R.      (* pi *)

  Definition mfp := 1 / (sqrt2 * pi * d * d * n).

  Lemma mfp_positive :
    n > 0 -> d > 0 -> mfp > 0.
  Admitted.

  Lemma mfp_monotone_decreasing :
    forall n1 n2 : R,
      n1 > 0 -> n2 > 0 -> n1 < n2 ->
      d > 0 -> mfp_with n1 > mfp_with n2.
  Admitted.
End MeanFreePath.

(* ---- Knudsen Number Properties ---- *)
(* Prove: Kn >= 0 when MFP >= 0 and L > 0 *)
(* Prove: Kn < 0.01 implies continuum regime *)

Section KnudsenNumber.
  Variable mfp : R.     (* mean free path [m] *)
  Variable L : R.       (* characteristic length [m] *)

  Definition kn := mfp / L.

  Lemma kn_nonneg :
    mfp >= 0 -> L > 0 -> kn >= 0.
  Admitted.

  Lemma kn_regime_transition :
    kn < 0.01 -> (* continuum *)
    True.
  Admitted.
End KnudsenNumber.

(* ---- Ballistic Coefficient Properties ---- *)
(* Prove: beta > 0 when m > 0, q >= 0, F_drag > 0 *)

Section BallisticCoeff.
  Variable m : R.       (* mass [kg] *)
  Variable q : R.       (* dynamic pressure [Pa] *)
  Variable F : R.       (* drag force [N] *)

  Definition beta := m * q / F.

  Lemma beta_positive :
    m > 0 -> q >= 0 -> F > 0 -> beta > 0.
  Admitted.

  Lemma beta_proportional_to_mass :
    (* Doubling mass doubles beta (q, F fixed) *)
    beta m q F = 2 * beta (m / 2) q F.
  Admitted.
End BallisticCoeff.

(* ---- Sutton-Graves Heat Flux Properties ---- *)
(* Prove: q_stag >= 0 for valid inputs *)
(* Prove: q_stag increases with velocity cubed *)

Section SuttonGraves.
  Variable rho : R.     (* density [kg/m^3] *)
  Variable Rn : R.      (* nose radius [m] *)
  Variable V : R.       (* velocity [m/s] *)
  Variable Csg : R.     (* Sutton-Graves constant *)

  Definition q_sg := Csg * sqrt (rho / Rn) * V * V * V.

  Lemma q_sg_nonneg :
    rho >= 0 -> Rn > 0 -> V >= 0 -> Csg > 0 -> q_sg >= 0.
  Admitted.

  Lemma q_sg_velocity_cubic :
    (* Scaling velocity by k scales heat flux by k^3 *)
    forall k : R, k > 0 ->
      q_sg rho Rn (k * V) = k * k * k * q_sg rho Rn V.
  Admitted.
End SuttonGraves.

(* ---- Survivability Envelope ---- *)
(* Prove: Is_Survivable implies all temps within limits *)

Section Survivability.
  Variable T_surface : R.
  Variable T_backface : R.
  Variable g_load : R.

  Variable SiC_max : R.     (* 2073 K *)
  Variable Kapton_max : R.  (* 773 K *)
  Variable g_max : R.       (* 25 g *)

  Definition survivable :=
    T_surface <= SiC_max /\
    T_backface <= Kapton_max /\
    g_load <= g_max.

  Lemma survivability_implies_temp_bounds :
    survivable ->
    T_surface <= SiC_max /\ T_backface <= Kapton_max.
  Admitted.

  Lemma survivability_implies_g_bound :
    survivable ->
    g_load <= g_max.
  Admitted.
End Survivability.
