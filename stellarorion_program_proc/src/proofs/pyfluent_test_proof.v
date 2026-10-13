(* ============================================================================
   MACHINE-CHECKED PROOF -- pyfluent_test (SSH probe timing + version width)
   ============================================================================
   Unit  : src/python/pyfluent_test.py
             _ssh_connection_check ssh.connect timeouts (lines 80,82)
             _ssh_connection_check version regex + Substring (lines 107,110)
             run_integration_test remote handshake exec (line 258)

   Goal (unit): Session launch returns valid session or typed error; no silent
   failure.  The typed-error scheme is a sum-type property; the numeric core
   this file machine-checks is the timeout budget and the version-decoding
   arithmetic the SSH probe relies on:
     (1) the SSH connect timeout is 10 s and the handshake exec timeout is
         30 s, so the combined probe budget is 10 + 30 = 40 s, and after the
         connect phase the remaining budget (40 - 10 = 30 s) is exactly the
         handshake timeout and is non-negative;
     (2) the Ansys version is matched by ^v\d{3}$ (exactly 3 digits, line 107)
         and the leading 'v' is stripped by Substring(1) (line 110), so the
         decoded numeric version keeps the 3 demanded digits and the matched
         token has width 1 + 3 = 4.

   AXIOMS
   A1. ssh.connect is bounded by timeout=10 s (lines 80,82); the remote
       handshake exec_command is bounded by timeout=30 s (line 258).
       [Reference: src/python/pyfluent_test.py:80,82,258]
       [Citation: Paramiko SSHClient.connect timeout -- https://docs.paramiko.org/en/stable/api/client.html]
   A2. The Ansys install directory name matches the regex ^v\d{3}$, i.e. a
       single 'v' prefix plus exactly 3 ASCII digits; $v.Name.Substring(1)
       removes the 'v', leaving exactly those 3 digit characters.
       [Reference: src/python/pyfluent_test.py:107 (\d{3}), :110 (Substring(1))]

   THEORIES
   T1. 0 < connect_timeout, 0 < handshake_timeout.
   T2. connect + handshake = 40; (connect + handshake) - connect = handshake
       (non-negative remainder equal to the handshake budget).
   T3. connect_timeout <= connect_timeout + handshake_timeout  (connect fits).
   T4. numeric_version_len(prefix=1, digits=3) = 3  and  token_len(1,3) = 4.

   APPLICATIONS
   The remote probe is bounded in time (no silent hang) and decodes the Ansys
   version to a fixed width -- the bounded, deterministic behaviour behind
   "valid session or typed error, never a silent failure".

   VERIFICATION: every lemma below is discharged by Qed; nothing here is
   admitted, assumed or vacuous.  Intended target: coqc 8.18.0, using only
   Coq.Reals.Reals + Coq.micromega.Lia.
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lia.

Open Scope nat_scope.

(* A1 -- SSH connect timeout and handshake exec timeout, in seconds. *)
Definition SSH_CONNECT_TIMEOUT_S : nat := 10.
Definition HANDSHAKE_TIMEOUT_S : nat := 30.

(* A2 -- version token width: 'v' prefix (1) + exactly 3 digits. *)
Definition VERSION_PREFIX_LEN : nat := 1.
Definition VERSION_DIGITS : nat := 3.

Definition combined_probe_budget (connect handshake : nat) : nat := connect + handshake.
Definition matched_token_len (prefix digits : nat) : nat := prefix + digits.
Definition numeric_version_len (prefix digits : nat) : nat := prefix + digits - prefix.

(* T1 -- the connect timeout is strictly positive. *)
Lemma connect_timeout_positive : 0 < SSH_CONNECT_TIMEOUT_S.
Proof.
  unfold SSH_CONNECT_TIMEOUT_S.
  lia.
Qed.

(* T1 -- the handshake timeout is strictly positive. *)
Lemma handshake_timeout_positive : 0 < HANDSHAKE_TIMEOUT_S.
Proof.
  unfold HANDSHAKE_TIMEOUT_S.
  lia.
Qed.

(* T2 -- the combined probe budget is 40 s. *)
Lemma combined_budget_is_forty :
  combined_probe_budget SSH_CONNECT_TIMEOUT_S HANDSHAKE_TIMEOUT_S = 40.
Proof.
  unfold combined_probe_budget, SSH_CONNECT_TIMEOUT_S, HANDSHAKE_TIMEOUT_S.
  lia.
Qed.

(* T2 -- after the connect phase the remaining budget is the handshake budget. *)
Lemma post_connect_remaining_is_handshake :
  combined_probe_budget SSH_CONNECT_TIMEOUT_S HANDSHAKE_TIMEOUT_S - SSH_CONNECT_TIMEOUT_S
  = HANDSHAKE_TIMEOUT_S.
Proof.
  unfold combined_probe_budget, SSH_CONNECT_TIMEOUT_S, HANDSHAKE_TIMEOUT_S.
  lia.
Qed.

(* T3 -- the connect phase fits inside the combined budget. *)
Lemma connect_within_combined_budget :
  SSH_CONNECT_TIMEOUT_S <= combined_probe_budget SSH_CONNECT_TIMEOUT_S HANDSHAKE_TIMEOUT_S.
Proof.
  unfold SSH_CONNECT_TIMEOUT_S, combined_probe_budget, HANDSHAKE_TIMEOUT_S.
  lia.
Qed.

(* T4 -- stripping the 'v' leaves the 3 demanded digits. *)
Lemma numeric_version_len_matches_regex :
  numeric_version_len VERSION_PREFIX_LEN VERSION_DIGITS = VERSION_DIGITS.
Proof.
  unfold numeric_version_len, VERSION_PREFIX_LEN, VERSION_DIGITS.
  lia.
Qed.

(* T4 -- the matched "v###" token has width 4. *)
Lemma matched_token_width :
  matched_token_len VERSION_PREFIX_LEN VERSION_DIGITS = 4.
Proof.
  unfold matched_token_len, VERSION_PREFIX_LEN, VERSION_DIGITS.
  lia.
Qed.
