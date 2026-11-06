; Utsa 0.1: deterministic, evidence-bearing MeTTa rules, no LLM or PLN claim.
; The host supplies only a permission-filtered, current-revision projection.
; Untrusted contribution text is NEVER parsed as MeTTa.

(= (exists $pattern)
   (not (== (collapse (match &self $pattern True)) ())))

(= (distinct-owners $a $b)
   (match &self (, (Record $a $oa $ka) (Record $b $ob $kb)
                  (Entity $a $ea) (Entity $b $eb))
     (and (not (== $oa $ob)) (not (== $ea $eb)))))

(= (later $a $b) (if (> $a $b) $a $b))
(= (earlier $a $b) (if (< $a $b) $a $b))
(= (window-hours $ns $ne $os $oe $now)
   (/ (- (earlier $ne $oe) (later $now (later $ns $os))) 3600))

; Every inference, including interests, requires both records to be permitted.
(= (pair-allowed $a $b)
   (and (and (exists (Eligible $a)) (exists (Eligible $b)))
        (distinct-owners $a $b)))

; Shared interests make no availability or ability assertion.
(= (interest $a $b)
   (match &self (, (Topic $a $t) (Topic $b $t))
     (if (pair-allowed $a $b)
         (SharedInterest $a $b $t)
         (empty))))

; Explicit capability -> requirement links only. No similarity transitivity.
(= (complement $n $o)
   (match &self (, (Record $n $pn need) (Record $o $po offer)
                  (Requires $n $capability) (Provides $o $capability))
     (if (and (pair-allowed $n $o) (exists (Confirmed $o)))
         (ComplementaryCapability $n $o $capability $capability direct)
         (empty))))

(= (complement $n $o)
   (match &self (, (Record $n $pn need) (Record $o $po offer)
                  (Requires $n $required) (Provides $o $capability)
                  (Domain $o $from) (Domain $n $to)
                  (Bridge $capability $required $from $to $evidence))
     (if (and (pair-allowed $n $o) (exists (Confirmed $o)))
         (ComplementaryCapability $n $o $capability $required $evidence)
         (empty))))

(= (compatible-term $a $b)
   (or (== $a $b) (or (== $a either) (== $b either))))
(= (conditions-clear $n $o)
   (match &self (, (Conditions $n $nm $nt $nc) (Conditions $o $om $ot $oc))
     (and (and (== $nc clear) (== $oc clear))
          (and (compatible-term $nm $om) (compatible-term $nt $ot)))))

; "Opportunity" means an actionable candidate, never consent or completion.
; Times are UTC epoch seconds. Windows are half-open: [start,end).
(= (opportunity $n $o)
   (let (ComplementaryCapability $n $o $cap $req $evidence) (complement $n $o)
     (match &self (, (Window $n $ns $ne) (Window $o $os $oe)
                    (Effort $n $demand) (Effort $o $capacity)
                    (Now $now))
       (if (and (and (exists (Available $n)) (exists (Available $o)))
                (and (and (exists (Actionable $n)) (conditions-clear $n $o))
                     (and (and (>= $capacity $demand)
                               (>= (window-hours $ns $ne $os $oe $now) $demand))
                          (and (< $ns $oe) (and (< $os $ne)
                               (and (< $now $ne) (< $now $oe)))))))
           (GenuineOpportunity $n $o $cap $req $evidence)
           (empty)))))

; Explanations of missing operational conditions, evaluated by the same runtime.
(= (blocker $n $o)
   (if (not (exists (Available $o))) OfferAvailabilityUnknown (empty)))
(= (blocker $n $o)
   (if (not (exists (Available $n))) NeedAvailabilityUnknown (empty)))
(= (blocker $n $o)
   (if (not (exists (Actionable $n))) NoConcreteNextAction (empty)))
(= (blocker $n $o)
   (if (not (conditions-clear $n $o)) ConditionsUnresolvedOrIncompatible (empty)))
(= (blocker $n $o)
   (match &self (, (Effort $n $demand) (Effort $o $capacity))
     (if (< $capacity $demand) InsufficientCapacity (empty))))
(= (blocker $n $o)
   (match &self (, (Window $n $ns $ne) (Window $o $os $oe) (Now $now))
     (if (not (and (< $ns $oe) (and (< $os $ne)
                   (and (< $now $ne) (< $now $oe)))))
         NoRemainingSharedWindow (empty))))
(= (blocker $n $o)
   (match &self (, (Window $n $ns $ne) (Window $o $os $oe)
                  (Now $now) (Effort $n $demand))
     (if (< (window-hours $ns $ne $os $oe $now) $demand)
         SharedWindowTooShort (empty))))

; Bilateral acceptance is scoped to exact source revisions.
; Actual contact-field disclosure remains a separately authorized host action.
; Revocation/freshness/permission are rechecked by evaluating the same rules.
(= (connection-ready $n $o)
   (let (GenuineOpportunity $n $o $cap $req $evidence) (opportunity $n $o)
     (if (and (exists (Accepted $n $o)) (exists (Accepted $o $n)))
         (ConnectionReady $n $o)
         (empty))))
