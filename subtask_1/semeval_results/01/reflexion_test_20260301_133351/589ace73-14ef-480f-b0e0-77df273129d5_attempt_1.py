% Facts for I premise (Some S are P) - not needed for this syllogism

% Rules from premises
structure_with_wheels(X) :- building(X).
building(X) :- house(X).

% Validity check: All houses are structures with wheels
valid_syllogism :- \+ (house(X), \+ structure_with_wheels(X)).