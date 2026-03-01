% Facts (witness: a bird that is both a vehicle and a building)
bird(sparrow).

% Rules from premises
building(X) :- bird(X).
vehicle(X) :- bird(X).

% Validity check: Some vehicles are buildings
valid_syllogism :- vehicle(X), building(X).