-- Narrative scope rule for the Rev_Nov27_2026.md decision.
-- Chapter 2 tracks the storyline and theory anchors; the appendix holds the
-- full derivations. Conversely, every appendix section must be motivated in
-- Chapter 2 first.
namespace NarrativeScope

inductive Topic where
  | knudsenRegime
  | viscousEntropy
  | frameworkChain
  | gnatproveTables
  | leanRocqIdentities
  | panelProvenance
deriving DecidableEq, Repr

def inChapter : Topic -> Bool
  | .knudsenRegime => true
  | .viscousEntropy => true
  | .frameworkChain => true
  | _ => false

def inAppendix : Topic -> Bool
  | .gnatproveTables => true
  | .leanRocqIdentities => true
  | .panelProvenance => true
  | _ => false

-- Under the scope rule, appendix content is introduced (motivated) in Ch2.
def describedInChapter : Topic -> Bool
  | .knudsenRegime => true
  | .viscousEntropy => true
  | .frameworkChain => true
  | .gnatproveTables => true
  | .leanRocqIdentities => true
  | .panelProvenance => true

def ScopeRule : Prop := ∀ t : Topic, inAppendix t = true -> describedInChapter t = true

theorem scope_rule_holds : ScopeRule := by
  intro t
  cases t <;> simp [inAppendix, describedInChapter]
end NarrativeScope