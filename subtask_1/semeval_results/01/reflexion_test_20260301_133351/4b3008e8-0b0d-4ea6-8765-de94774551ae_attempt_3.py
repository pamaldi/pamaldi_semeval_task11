% Facts for witnesses
squirrel(stripe).

% Rules from premises
non_biped(X) :- squirrel(X).

% E-premise constraint: No non-biped is a living creature
conflict :- non_biped(X), living_creature(X).

% living_creature has no facts, so we don't need a fail clause
% It will naturally fail for any query

% Validity check: Every squirrel is a living creature
valid_syllogism :- squirrel(X), living_creature(X).