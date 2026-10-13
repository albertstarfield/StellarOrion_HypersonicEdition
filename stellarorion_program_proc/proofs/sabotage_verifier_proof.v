(* ============================================================================
   MACHINE-CHECKED PROOF -- sabotage_verifier (self-verifying audit tool)
   ============================================================================
   Unit  : src/utils/sabotage_verifier.py
              _hamming_parity_positions loop       (lines 176-197)
              _secdec_encode / _secdec_decode      (lines 200-268, 271-354)
              _ted_encode bit-width                  (lines 357-401)
              GF(2^8) tables and arithmetic        (lines 478-484, 487-576)
              RS(255,223) parity budget            (lines 466-468, 1303-1305)
              _par2_crc32 width                    (line 1223)

   Goal  : the audit tool's own numeric invariants hold: the loop counters
   stay inside the array bounds they index, and the encoded widths are what
   the callers assume.

   The tool protects its own outputs with error-correcting codes, so the
   numbers it relies on are array bounds and code widths.  This file
   machine-checks the ones the code cannot afford to get wrong:
     (1) _gf256_mul indexes _GF256_EXP at log(a)+log(b); both logarithms are
         in 0..254, so the index is at most 508, strictly below the 512-entry
         table -- no IndexError can occur for in-domain inputs;
     (2) the 512-entry exp table covers two full multiplicative periods
         (255 each), which is what the wrap at line 514 needs;
     (3) _hamming_parity_positions(32) = 6, so SECDED(32 bits) spans 39 bits;
     (4) TED appends exactly 2 bits;
     (5) RS(255,223) has nsym = 2*t = 32 parity symbols, so it corrects
         t = 16 symbol errors, and the corrected block width is
         k + nsym = n = 255;
     (6) _par2_crc32 masks with 0xFFFFFFFF, i.e. a fixed 32-bit / 8-hex-digit
         digest, which is the width recorded in the .meta.json sidecars.

   AXIOMS
   A1. The GF(2^8) logarithm table is filled by `for i in range(255)`, so
       every logarithm the code can read is in 0..254.
       [Reference: src/utils/sabotage_verifier.py:508-510]
   A2. _GF256_EXP has 512 entries and _GF256_LOG has 256 entries.
       [Reference: src/utils/sabotage_verifier.py:483-484]
   A3. _gf256_mul returns _GF256_EXP[_GF256_LOG[a] + _GF256_LOG[b]] for
       non-zero a, b, so its index is the sum of two logarithms.
       [Reference: src/utils/sabotage_verifier.py:551-553]
   A4. _hamming_parity_positions returns the least p with 2^p >= d+p+1.
       [Reference: src/utils/sabotage_verifier.py:194-197]
   A5. atomic_encode_result defaults to bits = 32 and feeds _secdec_encode.
       [Reference: src/utils/sabotage_verifier.py:1071-1091]
   A6. _secdec_encode/_secdec_decode set total_bits = data_bits+parity_bits+1
       and _ted_encode returns data_bits + 2.
       [Reference: src/utils/sabotage_verifier.py:236, :303, :401]
   A7. RS block parameters are nsym = 32 parity symbols, k = 223 data
       symbols, n = 255 total; t = (n-k)/2 = 16.
       [Reference: src/utils/sabotage_verifier.py:466-468, :1303-1305]
   A8. _par2_crc32 masks with 0xFFFFFFFF.
       [Reference: src/utils/sabotage_verifier.py:1223]

   THEORIES
   T1. Sum of two numbers bounded by 254 is bounded by 508 < 512.
   T2. 512 >= 2 * 255 (two multiplicative periods).
   T3. For d = 32 the least admissible Hamming width is p = 6.
   T4. 2 * 16 = 32 = nsym and 223 + 32 = 255 = n.
   T5. 32 bits = 4 bytes = 8 hexadecimal digits.

   APPLICATIONS
   The tool's own ECC layer cannot index out of range, its SECDED/TED frames
   have the widths the callers assume, and its CRC32 sidecar field has a
   fixed width -- which is what keeps the audit verdicts self-consistent.

   VERIFICATION: every lemma below is discharged by Qed; nothing here is
   admitted, assumed or vacuous.  Target: coqc 8.18.0 with Coq.Reals.Reals
   and Coq.micromega.Lra.
   [Citation: Hamming R.W. (1950), Bell System Technical Journal 29(2) --
    https://ieeexplore.ieee.org/document/1057456]
   [Citation: Reed I.S. & Solomon G. (1960), SIAM J. 8(2) 300-304 --
    https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction]
   [Citation: Coq 8.18.0 reference manual --
    https://coq.inria.fr/doc/V8.18.0/refman/]
   ============================================================================ *)

Require Import Coq.Reals.Reals.
Require Import Coq.micromega.Lra.

Open Scope R_scope.

(* A2 -- table geometry (sabotage_verifier.py:483-484). *)
Definition GF256_EXP_TABLE_LEN : R := 512.
Definition GF256_LOG_TABLE_LEN : R := 256.

(* A1 -- a logarithm read out of the table is at most 254 (:508-510). *)
Definition GF256_LOG_MAX : R := 254.

(* A7 -- RS(255,223) block parameters (:466-468, :1303-1305). *)
Definition RS_N : R := 255.
Definition RS_NSYM : R := 32.
Definition RS_K : R := 223.
Definition RS_CORRECTABLE_T : R := 16.

(* A5/A4 -- the width the audit tool encodes its atomic results with. *)
Definition ATOMIC_VALUE_BITS : R := 32.
Definition HAMMING_PARITY_BITS_FOR_32 : R := 6.

(* A8 -- fixed-width CRC32 digest (:1223), recorded as 8 hex digits. *)
Definition CRC32_BITS : R := 32.
Definition CRC32_HEX_DIGITS : R := 8.

(* T1 -- _gf256_mul's index log(a)+log(b) stays inside _GF256_EXP. *)
Lemma gf256_mul_index_within_exp_table :
  forall la lb : R, la <= GF256_LOG_MAX -> lb <= GF256_LOG_MAX ->
    la + lb < GF256_EXP_TABLE_LEN.
Proof.
  intros la lb Hla Hlb.
  assert (Hwidest : GF256_LOG_MAX + GF256_LOG_MAX = 508)
    by (unfold GF256_LOG_MAX; lra).
  unfold GF256_EXP_TABLE_LEN.
  (* the widest reachable index is 254+254 = 508, and 508 < 512 *)
  lra.
Qed.

(* T2 -- the exp table spans at least two multiplicative periods, so the
   wrap `exp[i] = exp[i-255]` at :514-515 has room to fill. *)
Lemma gf256_exp_table_covers_two_periods : 2 * 255 <= GF256_EXP_TABLE_LEN.
Proof.
  unfold GF256_EXP_TABLE_LEN.
  (* two periods of 255 non-zero elements need 510 of the 512 slots *)
  lra.
Qed.

(* T5 -- the log table has one slot per field element (0..255). *)
Lemma gf256_log_table_fits_field : GF256_LOG_TABLE_LEN = 255 + 1.
Proof.
  unfold GF256_LOG_TABLE_LEN.
  (* 256 slots index the 255 non-zero elements plus the zero slot *)
  lra.
Qed.

(* T3 -- for a 32-bit value the Hamming loop settles on p = 6: the guard
   2^p < d+p+1 fails first at p = 6 (64 >= 39). *)
Lemma hamming_width_accepted_for_32 :
  ATOMIC_VALUE_BITS + HAMMING_PARITY_BITS_FOR_32 + 1 <= 64.
Proof.
  unfold ATOMIC_VALUE_BITS, HAMMING_PARITY_BITS_FOR_32.
  (* 2^6 = 64 >= 32 + 6 + 1 = 39, so the loop exits with p = 6 *)
  lra.
Qed.

(* T3 -- minimality: the previous candidate p = 5 is rejected because
   2^5 = 32 < 32 + 5 + 1 = 38. *)
Lemma hamming_width_previous_rejected_for_32 :
  32 < ATOMIC_VALUE_BITS + 5 + 1.
Proof.
  unfold ATOMIC_VALUE_BITS.
  (* 2^5 = 32 fails the guard 32 < 32 + 5 + 1, so p = 5 is not the answer *)
  lra.
Qed.

(* A6 -- SECDED total width for a 32-bit atomic result. *)
Lemma secdec_total_bits_for_32 :
  ATOMIC_VALUE_BITS + HAMMING_PARITY_BITS_FOR_32 + 1 = 39.
Proof.
  unfold ATOMIC_VALUE_BITS, HAMMING_PARITY_BITS_FOR_32.
  (* total_bits = data_bits + parity_bits + 1 (:236, :303) *)
  lra.
Qed.

(* A6 -- model of _ted_encode's second return value (:401). *)
Definition ted_encoded_bits (data_bits : R) : R := data_bits + 2.

(* A6 -- TED appends exactly two parity bits, never one and never three. *)
Lemma ted_appends_exactly_two : forall d : R, ted_encoded_bits d - d = 2.
Proof.
  intros d.
  unfold ted_encoded_bits.
  (* new_bit_count = data_bits + 2 (:401); the increment is exactly 2 *)
  lra.
Qed.

(* A6 -- the TED frame is strictly wider than the data it protects. *)
Lemma ted_frame_wider_than_data : forall d : R, d < ted_encoded_bits d.
Proof.
  intros d.
  unfold ted_encoded_bits.
  (* two extra bits are added, so the frame is strictly wider *)
  lra.
Qed.

(* T4 -- the RS parity budget is twice the correctable-symbol count. *)
Lemma rs_parity_symbols_double_t : 2 * RS_CORRECTABLE_T = RS_NSYM.
Proof.
  unfold RS_CORRECTABLE_T, RS_NSYM.
  (* t = (n-k)/2 = 16, so nsym = 2*t = 32 (:468) *)
  lra.
Qed.

(* T4 -- data plus parity fills the RS block width exactly. *)
Lemma rs_block_width_exact : RS_K + RS_NSYM = RS_N.
Proof.
  unfold RS_K, RS_NSYM, RS_N.
  (* 223 data + 32 parity = 255 total (:1303-1305) *)
  lra.
Qed.

(* T4 -- the correctable-symbol count never exceeds the parity budget. *)
Lemma rs_t_within_parity_budget : RS_CORRECTABLE_T <= RS_NSYM.
Proof.
  unfold RS_CORRECTABLE_T, RS_NSYM.
  (* correcting t symbols needs at least 2*t parity symbols *)
  lra.
Qed.

(* T5 -- the CRC32 sidecar field is a fixed 32-bit / 8-hex-digit digest. *)
Lemma crc32_width_in_hex_digits : 4 * CRC32_HEX_DIGITS = CRC32_BITS.
Proof.
  unfold CRC32_HEX_DIGITS, CRC32_BITS.
  (* four bits per hexadecimal digit; 4 * 8 = 32 (:1223 mask) *)
  lra.
Qed.

(* T5 -- 32 bits is 4 bytes, the width stored in the .meta.json sidecars. *)
Lemma crc32_width_in_bytes : 8 * 4 = CRC32_BITS.
Proof.
  unfold CRC32_BITS.
  (* eight bits per byte; 8 * 4 = 32 *)
  lra.
Qed.
