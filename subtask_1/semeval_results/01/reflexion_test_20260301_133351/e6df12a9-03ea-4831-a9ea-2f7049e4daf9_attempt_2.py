% COUNTEREXAMPLE: Doctor and bus driver are disjoint groups
% Both use the uniform category but have no overlap

% Witnesses
doctor(doc1).
uniform(doc1).

bus_driver(bus1).

% Rules from premises
% E-premise: No bus driver is a uniform-wearer
conflict :- bus_driver(X), uniform(X).

% I-premise: Some doctors are uniform-wearers
% (Already established by doctor(doc1), uniform(doc1))

% Validity check: Some doctors are bus drivers
valid_syllogism :- doctor(X), bus_driver(X).