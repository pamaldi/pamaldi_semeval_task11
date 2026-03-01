% Facts (witness: someone who is gold)
person(alice).
gold(alice).

% Rule from A-premise: All things which are gold are metals
metal(X) :- gold(X).

% Validity check: Some metals are people
valid_syllogism :- metal(X), person(X).