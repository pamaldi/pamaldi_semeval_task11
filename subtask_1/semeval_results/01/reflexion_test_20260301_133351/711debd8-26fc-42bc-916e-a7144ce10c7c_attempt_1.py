% Facts (witness: a tent that is NOT a building)
tent(t1).

% Fail clauses
building(_) :- fail.
house(_) :- fail.

% Rule from A-premise: All houses are buildings
building(X) :- house(X).

% I-premise constraint: Some tents are not buildings
% (t1 is a tent that is not a building)

% E-premise constraint: No house is a tent (implicit in the model)
% (since house/1 has no facts, and tent(t1) is not a house)

% Validity check: Some tents are not houses
valid_syllogism :- tent(X), \+ house(X).