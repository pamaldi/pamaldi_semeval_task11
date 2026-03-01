% Counterexample: human exists who is a bird but cannot fly

human(alice).
bird(alice).

% E-premise constraint: No bird can fly
conflict :- bird(X), fly(X).

% Rule from A-premise: All birds are humans
% (no need to encode explicitly - already satisfied by our facts)

% Validity check: E-conclusion "No human can fly"
valid_syllogism :- \+ (human(X), fly(X)).