% Counterexample: human exists who is a bird and cannot fly

% Entities
human(alice).
bird(alice).

% E-premise constraint: No bird can fly
conflict :- bird(X), fly(X).

% fly/1 has NO facts and is not used in premises
fly(_) :- fail.

% Rule from A-premise: All birds are humans
% (no need to encode explicitly - already satisfied by our facts)

% Validity check: A-conclusion "All humans can fly" is INVALID
% We need to show that there exists a human who cannot fly
valid_syllogism :- human(X), \+ fly(X).