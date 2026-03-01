% Witness: copper that is a conductor
copper(c1).
metal(c1).
conductor(c1).

% Rule from first premise: All metals are conductors
conductor(X) :- metal(X).

% Rule from second premise: All copper is metal
metal(X) :- copper(X).

% Validity check: Some copper is a conductor
valid_syllogism :- copper(X), conductor(X).