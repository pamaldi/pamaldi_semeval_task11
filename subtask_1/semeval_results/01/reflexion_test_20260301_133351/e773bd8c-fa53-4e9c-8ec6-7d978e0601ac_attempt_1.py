% Facts (witnesses)
boat(sailboat1).
\+ fly(sailboat1).  % Some boats cannot fly

% Rule from premise: Every object can fly
fly(X) :- object(X).

% Validity check: Some boats are not objects
valid_syllogism :- boat(X), \+ object(X).