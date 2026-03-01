% Facts (minimal model - only what's needed for premises)
tiger(simba).

% Rules from premises
feline(X) :- tiger(X).
mammal(X) :- tiger(X).

% Mammal is not restricted to tigers (counterexample construction)
% So no fail clause for mammal/1

% Validity check: Some mammals are NOT felines
valid_syllogism :- mammal(X), \+ feline(X).