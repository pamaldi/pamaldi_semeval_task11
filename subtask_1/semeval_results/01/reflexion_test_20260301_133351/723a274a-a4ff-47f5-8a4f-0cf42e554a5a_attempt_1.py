% Fail clause for child/1 (no children exist in this model)
child(_) :- fail.

% A-premise: No adult is a child
conflict :- adult(X), child(X).

% I-premise: Some people are adults
adult(adult1).
person(adult1).

% I-conclusion: Some people are children
valid_syllogism :- person(X), child(X).