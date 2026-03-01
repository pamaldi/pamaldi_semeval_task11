% Witnesses
milk1.
liquid(milk1).

% beverage has NO facts
beverage(_) :- fail.

% E-premise constraint: No liquid is a beverage
conflict :- liquid(X), beverage(X).

% O-conclusion: Some milk is not a beverage
valid_syllogism :- milk1, \+ beverage(milk1).