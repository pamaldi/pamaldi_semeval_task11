% Facts for children and athletes
child(alice).
athlete(alice).

% professors has no facts and is not allowed to be children
professor(_) :- fail.

% E-premise: No professors are children
conflict :- professor(X), child(X).

% Validity check: Some professors are athletes
valid_syllogism :- professor(X), athlete(X).