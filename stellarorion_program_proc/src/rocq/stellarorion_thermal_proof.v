(* StellarOrion HypersonicEdition — Thermal Model Proof Skeletons
   ==============================================================
   1D transient backface temperature model proofs.
   T_back = T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta)

   Author: Albert Starfield Wahyu Suryo Samudro *)

Section BackfaceTemperature.
  Variable T_init : R.      (* initial temperature [K] *)
  Variable q : R.            (* heat flux [W/m^2] *)
  Variable dt : R.           (* time step [s] *)
  Variable eta_lag : R.      (* thermal lag efficiency *)
  Variable rho_TPS : R.      (* TPS density [kg/m^3] *)
  Variable Cp : R.           (* TPS specific heat [J/(kg*K)] *)
  Variable delta : R.        (* TPS thickness [m] *)

  Definition T_back :=
    T_init + (q * dt * eta_lag) / (rho_TPS * Cp * delta).

  Lemma T_back_nonneg :
    T_init >= 0 -> q >= 0 -> dt >= 0 -> eta_lag > 0 ->
    rho_TPS > 0 -> Cp > 0 -> delta > 0 ->
    T_back >= 0.
  Admitted.

  Lemma T_back_increases_with_heat :
    (* Higher heat flux → higher backface temperature *)
    forall q1 q2 : R,
      q1 >= 0 -> q2 > q1 ->
      eta_lag > 0 -> dt >= 0 ->
      rho_TPS > 0 -> Cp > 0 -> delta > 0 ->
      T_init >= 0 ->
      T_back_with q2 > T_back_with q1.
  Admitted.

  Lemma T_back_linear_in_q :
    (* Backface temperature is linear in heat flux *)
    forall q1 q2 : R,
      T_back_with (q1 + q2) = T_back_with q1 + T_back_with q2 - T_init.
  Admitted.
End BackfaceTemperature.

(* ---- Radiative Equilibrium Temperature ---- *)
(* T = (q / (sigma * epsilon))^(1/4) *)

Section RadiativeEquilibrium.
  Variable q : R.           (* heat flux [W/m^2] *)
  Variable sigma : R.       (* Stefan-Boltzmann constant *)
  Variable epsilon : R.     (* emissivity *)

  Definition T_rad := (q / (sigma * epsilon))^(1/4).

  Lemma T_rad_nonneg :
    q >= 0 -> sigma > 0 -> epsilon > 0 -> T_rad >= 0.
  Admitted.

  Lemma T_radFourth_proportional :
    (* T^4 is proportional to q *)
    T_rad^4 = q / (sigma * epsilon).
  Admitted.
End RadiativeEquilibrium.
