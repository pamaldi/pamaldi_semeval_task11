% Facts: No witness for piano or musical instrument yet, building counterexample

% Fail clauses for completely empty predicates
piano(_) :- fail.
musical_instrument(_) :- fail.
object(_) :- fail.

% Rules from premises
musical_instrument(X) :- piano(X).
object(X) :- musical_instrument(X).

% Validity check: Some objects are pianos
valid_syllogism :- object(X), piano(X).