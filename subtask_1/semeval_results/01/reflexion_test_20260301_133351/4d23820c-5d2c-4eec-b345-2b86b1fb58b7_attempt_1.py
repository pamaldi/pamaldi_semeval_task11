% Facts for the counterexample
doctor(john).
human(john).

% Rules from the premises
mammal(X) :- human(X).
human(X) :- doctor(X).

% Validity check for the conclusion: Some doctors are not mammals
valid_syllogism :- doctor(X), \+ mammal(X).