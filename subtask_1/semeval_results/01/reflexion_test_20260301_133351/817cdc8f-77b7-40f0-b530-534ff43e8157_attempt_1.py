% Facts: chemist has a witness (counterexample candidate)
chemist(alice).

% Fail clause: scientist has no facts, only derived
scientist(_) :- fail.

% Rules
researcher(X) :- scientist(X).  % All scientists are researchers
conflict :- chemist(X), researcher(X).  % No chemist can be a researcher

% Validity check: No chemist is a scientist
valid_syllogism :- \+ (chemist(X), scientist(X)).